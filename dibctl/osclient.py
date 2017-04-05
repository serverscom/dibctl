import glanceclient
from keystoneauth1 import identity
from keystoneauth1 import session
import novaclient.client
import re
from functools import partial
import requests
import urllib3
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import simplejson
import copy


class UnknownPolicy(ValueError):
    pass


class OpenStackError(EnvironmentError):
    pass


class AuthError(OpenStackError):
    pass


class CredNotFound(AuthError):
    pass


class DiscoveryError(OpenStackError):
    pass


class MissmatchError(OpenStackError):
    pass


class UploadError(OpenStackError):
    pass


class UploadDeletedError(UploadError):
    pass


class UploadNotDeletedError(UploadError):
    pass


class IPError(OpenStackError):
    pass


class NoIPFoundError(IPError):
    pass


class MultipleIPError(IPError):
    pass


# all those '_smart' functions should be somewhere in config part...
def _smart_merge(target, key, orig1, orig2, policy='second'):
    if policy == 'first':  # orig1 have priority over orig2
        if key in orig1:
            target[key] = orig1[key]
        elif key in orig2:
            target[key] = orig2[key]
    elif policy == 'second':  # orig2 have priority over orig1
        if key in orig2:
            target[key] = orig2[key]
        elif key in orig1:
            target[key] = orig1[key]
    elif policy == 'mergelist':  # for lists
        if key in orig1 or key in orig2:
            target[key] = orig1.get(key, []) + orig2.get(key, [])
    elif policy == 'mergedict':  # for dicts
        if key in orig1 or key in orig2:
            target[key] = copy.deepcopy(orig1.get(key, {}))
            target[key].update(orig2.get(key, {}))
    elif policy == 'max':  # (num types only), use the maximum value
        if key in orig1 or key in orig2:
            target[key] = max(orig1.get(key, None), orig2.get(key, None))
    else:
        raise UnknownPolicy("Policy %s is unknown, can't merge" % policy)


def smart_join_glance_config(img_conf, env_conf):
    '''
        join together two glance sections with
        special logic for each field during merge.
    '''
    # default policy is 'second', so we'll join both, and than process special cases
    common_config = copy.deepcopy(env_conf)
    # should cover 'name' and 'public'
    common_config.update(img_conf)
    for key, policy in (
        ('api_version', 'second'),  # test/upload_env has priority here
        ('upload_timeout', 'max'),
        ('properties', 'mergedict'),  # envs has priority on conflicting entries
        ('tags', 'mergelist'),
        ('endpoint', 'second'),  # envs has priority. I don't know why anyone wants to put endpoint into image config.
    ):
        _smart_merge(common_config, key, img_conf, env_conf, policy)
    return common_config


class OSClient(object):
    OS_CACERT = '/etc/ssl/certs'
    OBSOLETE_PREFIX = "Obsolete"
    OBSOLETE_PROP = "obsolete"
    SUPPORTED_VERSIONS = set(('v2', 'v3'))
    OPTION_NAMINGS = {
        'username': {
            'names': (
                'os_username', 'os_user_name' 'username', 'user_name',
                'user', 'os_user', 'username'
            ),
            'default': None
        },
        'password': {
            'names': ('os_password', 'password', 'pass', 'os_pass'),
            'default': None
        },
        'project': {
            'names': (
                'os_tenant_name', 'os_tenantname', 'tenant_name', 'tenantname',
                'tenant', 'project', 'project_name', 'projectname'
            ),
            'default': None
        },
        'auth_url': {
            'names': (
                'os_auth_url', 'os_auth_uri', 'auth_uri',
                'auth_url', 'url', 'uri'
            ),
            'default': None
        },
        'user_domain': {
            'names': (
                'os_user_domain', 'user_domain', 'os_userdomain', 'userdomain',
                'os_user_domain_name', 'user_domain_name'
            ),
            'default': 'default'
        },
        'project_domain': {
            'names': (
                'os_project_domain', 'project_domain', 'os_projectdomain',
                'projectdomain', 'os_project_domain_name', 'project_domain_name'
            ),
            'default': 'default'
        }
    }
    OPTIONS_MAPPING = {  # how to name: where to take
        'v2': {
            #  http://docs.openstack.org/developer/keystoneauth/api/keystoneauth1.identity.html
            'auth_url': 'auth_url',
            'tenant_name': 'project',
            'username': 'username',
            'password': 'password',
        },
        'v3': {
            #  http://docs.openstack.org/developer/keystoneauth/api/keystoneauth1.identity.v3.html
            'username': 'username',
            'password': 'password',
            'user_domain_name': 'user_domain',
            'project_domain_name': 'project_domain',
            'auth_url': 'auth_url',
            'project_name': 'project'
        }
    }

    def __init__(
        self,
        keystone_data,
        nova_data,
        glance_data,
        neutron_data,
        overrides={},
        ca_path='/etc/ssl/certs',
        insecure=False,
        disable_warnings=False
    ):

        if disable_warnings:
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
            urllib3.disable_warnings()
        self._set_api_version(dict(keystone_data), insecure)
        self.auth = self._prepare_auth(dict(keystone_data), overrides)
        self.session = self.create_session(self.api_version, self.auth, insecure)
        self.nova = self.get_nova(self.session)
        self.glance = self.get_glance(self.session)

    @staticmethod
    def create_session(api_version, auth_data, insecure, timeout=30):
        verify = not insecure
        if api_version == 'v2':
            auth = identity.v2.Password(**auth_data)
        elif api_version == 'v3':
            auth = identity.v3.Password(**auth_data)
        else:
            raise DiscoveryError('Auth version %s is not supported' % api_version)

        # TODO we need to respect CACERT!
        return session.Session(
            auth=auth,
            user_agent='dibctl',
            verify=verify,
            timeout=timeout
        )

    @staticmethod
    def get_nova(session):
        return novaclient.client.Client('2', session=session)

    @staticmethod
    def get_glance(session):
        # TODO support for 'v2'
        return glanceclient.client.Client('1', session=session)

    @staticmethod
    def _get_generic_field(lowpriority, hipriority, target, cfg):
        for name in cfg['names']:
            for key in hipriority:
                if name == key.lower():
                    return {target: hipriority[key]}
        for name in cfg['names']:
            for key in lowpriority:
                if name == key.lower():
                    return {target: lowpriority[key]}
        if cfg['default']:
            return {target: cfg['default']}
        raise CredNotFound('Unable to find value for %s. '
                           'Aliases (case-insensitive): %s' %
                           (target, ', '.join(cfg['names'])))

    @staticmethod
    def map_creds(creds, version, global_mapping):
        new_creds = {}
        for target_name, cred_name in global_mapping[version].iteritems():
            new_creds[target_name] = creds[cred_name]
        return new_creds

    def _prepare_auth(self, keystone_data, overrides):
        filtered_overrides = {k: v for k, v in overrides.items() if k.startswith('OS_')}
        creds = {}
        for name in filtered_overrides.keys():
            print("Found %s in the environment, will use it" % name)
        for target, cfg in self.OPTION_NAMINGS.iteritems():
            creds.update(self._get_generic_field(keystone_data, filtered_overrides, target, cfg))
        return self.map_creds(creds, self.api_version, self.OPTIONS_MAPPING)

    def _set_api_version(self, keystone_data, insecure):
        local_versions = self._find_local_versions()
        if 'api_version' in keystone_data:
            force_api_version = keystone_data['api_version']
            if self._issupported_version(force_api_version, local_versions):
                self.api_version = force_api_version
            else:
                raise DiscoveryError(
                    'API version %s for keystone is not supported' %
                    force_api_version
                )
        else:
            try:
                self.api_version = self._ask_for_version(
                    keystone_data,
                    local_versions,
                    insecure
                )
            except DiscoveryError as e:
                message = 'Unable to discover keystone version.' \
                          'Try to use "version" variable to force specific version.' \
                          'Error details: ' + str(e)
                raise DiscoveryError(message)

    def _issupported_version(self, version, lib_versions):
        return version in (set(lib_versions) & self.SUPPORTED_VERSIONS)

    @staticmethod
    def _major_version(version):
        unsupported = 'unsupported'
        try:
            v = str(version)
            if v[0] != 'v':
                return unsupported
            major = v[1]
            if 1 < int(major) < 9:
                return 'v' + major
            else:
                return unsupported
        except (KeyError, IndexError, ValueError):
            return unsupported

    @staticmethod
    def _find_local_versions():
        version_filter = partial(re.match, '^v\d+$')
        return filter(version_filter, dir(identity))

    def _ask_for_version(self, keystone_data, lib_versions, insecure):
        try:
            r = requests.get(keystone_data['auth_url'], verify=not insecure).json()
            if 'version' in r:
                versions = [r['version']['id']]
            else:
                versions = map(lambda x: x['id'], r['versions']['values'])
            for version in versions:
                major = self._major_version(version)
                if self._issupported_version(major, lib_versions):
                    return major
        except (requests.exceptions.ConnectionError, TypeError, KeyError, simplejson.scanner.JSONDecodeError) as e:
            raise DiscoveryError(e.message)

        message = "Unable to find common version to use for keystone authorisation." \
                  "keystoneauth1 library supports: {lib_versions}," \
                  "remote server supports: {remote_versions}," \
                  "this application supports: {app_versions} ".format(
                    lib_versions=str(lib_versions),
                    remote_versions=str(versions),
                    app_versions=str(self.SUPPORTED_VERSIONS)
                  )
        raise MissmatchError(message)

    def upload_image(
        self,
        name,
        filename,
        public=False,
        disk_format="qcow2",
        container_format="bare",
        share_with_tenants=[],
        meta={}
    ):
        img = self.glance.images.create(
            name=name,
            is_public=str(public),
            disk_format="qcow2",
            container_format="bare",
            data=open(filename, 'rb',  buffering=65536),
            properties=meta
        )

        if share_with_tenants:
            self.share_image(img, share_with_tenants)

        return img

    def share_image(self, img, tenant_name_list):
        raise NotImplementedError("Image sharing not implemented!")

    def older_images(self, image_name, image_uuid):
        all_duplicates = list(self.glance.images.list(filters={"name": image_name}))
        return set(map(lambda x: x.id, all_duplicates)) - set((image_uuid,))

    def mark_image_obsolete(self, name, uuid):
        obsoleted_name = self.OBSOLETE_PREFIX + " " + name
        meta = {self.OBSOLETE_PROP: str(True)}
        return self.glance.images.update(uuid, name=obsoleted_name, properties=meta)

    def get_image(self, uuid):
        return self.glance.images.get(uuid)

    def delete_image(self, image):
        self.glance.images.delete(image)

    def new_keypair(self, name):
        return self.nova.keypairs.create(name)

    def boot_instance(self, name, image_uuid, flavor, key_name, nic_list, config_drive=None, availability_zone=None):
        instance = self.nova.servers.create(
            name,
            image_uuid,
            flavor,
            key_name=key_name,
            nics=nic_list,
            config_drive=config_drive,
            availability_zone=availability_zone
        )
        return instance

    def get_instance(self, instance_uuid):
        return self.nova.servers.get(instance_uuid)

    def delete_instance(self, uuid):
        self.nova.servers.delete(uuid)

    def delete_keypair(self, key):
        self.nova.keypairs.delete(key)

    def fuzzy_find_flavor(self, flavor):
        try:
            flavor = self.nova.flavors.find(id=flavor)
        except:  # BAD! FIXME
            flavor = self.nova.flavors.find(name=flavor)
        return flavor

    def get_flavor(self, flavor):
        return self.nova.flavors.find(id=flavor)

    @staticmethod
    def get_instance_ip(instance, regexp):
        'return IP for instance in a ginven network'
        found = []
        if regexp:
            for network_name, ip in instance.networks.iteritems():
                if re.search(regexp, network_name):
                    found.append(ip)
        else:
            found = instance.networks.values()

        if len(found) > 1:
                raise MultipleIPError("More than one network match: %s, matching regexp is '%s'" % (
                    str(found),
                    str(regexp)
                ))
        elif len(found) == 1:
                return found[0][0]
        else:
            raise NoIPFoundError("No matching IP found. Search regexp: %s, networks: %s" % (
                str(regexp), str(instance.networks.values())))
