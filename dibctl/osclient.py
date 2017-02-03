#  deliports
import keystoneclient


import glanceclient
from keystoneauth1 import identity
from keystoneauth1 import session
import novaclient.client
import re
from functools import partial
import requests
import simplejson


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

    def new__init__(
        self,
        keystone_data,
        nova_data,
        glance_data,
        neutron_data,
        overrides={},
        ca_path='/etc/ssl/certs',
        insecure=False
    ):
        self._set_auth_version(keystone_data, insecure)
        self.auth = self._prepare_auth(keystone_data, overrides)
        self.session = self.create_session(self.auth_version, self.auth, insecure)
        self.nova = self.get_nova(self.session)
        self.glance = self.get_glance(self.session)

    @staticmethod
    def create_session(auth_version, auth_data, insecure, timeout=30):
        verify = not insecure
        print auth_data, auth_version
        if auth_version == 'v2':
            auth = identity.v2.Password(**auth_data)
        elif auth_version == 'v3':
            auth = identity.v3.Password(**auth_data)
        else:
            raise DiscoveryError('Auth version %s is not supported' % auth_version)

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
        creds = {}
        for target, cfg in self.OPTION_NAMINGS.iteritems():
            creds.update(self._get_generic_field(keystone_data, overrides, target, cfg))
        return self.map_creds(creds, self.auth_version, self.OPTIONS_MAPPING)

    def _set_auth_version(self, keystone_data, insecure):
        local_versions = self._find_local_versions()
        if 'api_version' in keystone_data:
            force_auth_version = keystone_data['api_version']
            if self._issupported_version(force_auth_version, local_versions):
                self.auth_version = force_auth_version
            else:
                raise DiscoveryError(
                    'API version %s for keystone is not supported' %
                    force_auth_version
                )
        else:
            try:
                self.auth_version = self._ask_for_version(
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

    def transitional_init(self, os_auth_url, os_tenant_name, os_username, os_password, insecure=False):
        self.os_creds = {
            "auth_url": os_auth_url,
            "tenant_name": os_tenant_name,
            "username": os_username,
            "password": os_password,
        }
        self.insecure = insecure
        print self.os_creds, insecure
        self.new__init__(self.os_creds, {}, {}, {}, {}, insecure=insecure)

    __init__ = transitional_init

    def old__init__(self, os_auth_url, os_tenant_name, os_username, os_password, insecure=False):
        self.os_creds = {
            "auth_url": os_auth_url,
            "tenant_name": os_tenant_name,
            "username": os_username,
            "password": os_password,
            "insecure": insecure
        }
        self.insecure = insecure
        self.init_keystone(os_auth_url, os_tenant_name, os_username, os_password)
        self.init_glance()
        self.init_nova()

    def init_keystone(self, os_auth_url, os_tenant_name, os_username, os_password):
        self.keystone_auth = keystoneclient.v2_0.Client(
            **self.os_creds
        )
        self.token = self.keystone_auth.get_token(self.keystone_auth.session)
        self.glance_endpoint = self.keystone_auth.service_catalog.url_for(
            service_type="image",
            endpoint_type="publicURL"
        )

    def init_glance(self):
        self.glance = glanceclient.Client(
            version="1",
            endpoint=self.glance_endpoint,
            token=self.token,
            cacert=self.OS_CACERT,
            insecure=self.insecure
        )

    def init_nova(self):
        self.nova = novaclient.client.Client(
            version="2",
            username=self.os_creds["username"],
            password=self.os_creds["password"],
            project_id=self.os_creds["tenant_name"],
            auth_url=self.os_creds["auth_url"],
            cacert=self.OS_CACERT,
            insecure=self.insecure
        )

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

        return img.id

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

    def boot_instance(self, name, image_uuid, flavor, key_name, nic_list, config_drive=None):
        instance = self.nova.servers.create(
            name,
            image_uuid,
            flavor,
            key_name=key_name,
            nics=nic_list,
            config_drive=config_drive
        )
        return instance

    def get_instance(self, instance_uuid):
        return self.nova.servers.get(instance_uuid)

    def delete_instance(self, uuid):
        self.nova.servers.delete(uuid)

    def delete_keypair(self, key):
        self.nova.keypairs.delete(key)

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
                raise MultipleIPError("More than one network match: %s" % str(found))
        elif len(found) == 1:
                return found[0][0]
        else:
            raise NoIPFoundError("No matching IP found")
