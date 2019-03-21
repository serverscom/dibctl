import osclient
import timeout
import sys
import uuid
import socket
import time
import os
import json
import config
import ssh
import ipaddress


class TimeoutError(EnvironmentError):
    pass


class InstanceError(EnvironmentError):
    pass


class PreparationError(EnvironmentError):
    pass


class FlavorError(EnvironmentError):
    pass


class PrepOS(object):
    '''
        Provides test-specific image/instance/keypair
        with timeouts and cleanup at errors
    '''
    LONG_OS_TIMEOUT = 360
    SHORT_OS_TIMEOUT = 10
    SLEEP_DELAY = 3

    def __init__(self, image, test_environment, override_image=None,
                 delete_image=True, delete_instance=True):
        self.os = None
        self.set_timeouts(image, test_environment)
        self.test_environment = test_environment
        self.report = True  # refactor me!
        if override_image:
            self.prepare_override_image(image, override_image)
        else:
            self.prepare_normal_image(image, delete_image)

        self.prepare_key()
        self.prepare_instance(test_environment, delete_instance)
        self.ssh = None
        self.combined_glance_section = osclient.smart_join_glance_config(
            image.get('glance', {}),
            test_environment.get('glance', {})
        )

    def set_timeouts(self, image_item, tenv_item):
        self.upload_timeout = config.get_max(
            image_item,
            tenv_item,
            'glance.upload_timeout',
            self.LONG_OS_TIMEOUT
        )
        self.keypair_timeout = config.get_max(
            image_item,
            tenv_item,
            'nova.keypair_timeout',
            self.SHORT_OS_TIMEOUT
        )
        self.cleanup_timeout = config.get_max(
            image_item,
            tenv_item,
            'nova.cleanup_timeout',
            self.SHORT_OS_TIMEOUT
        )
        self.active_timeout = config.get_max(
            image_item,
            tenv_item,
            'nova.active_timeout',
            self.LONG_OS_TIMEOUT
        )
        self.create_timeout = config.get_max(
            image_item,
            tenv_item,
            'nova.create_timeout',
            self.LONG_OS_TIMEOUT
        )

    def prepare_normal_image(self, image_item, delete_image_flag):
        self.image = image_item
        self.image_name = self.make_test_name(image_item['glance']['name'])
        self.delete_image = delete_image_flag
        self.os_image = None
        self.override_image = False
        self.image_was_removed = False

    def prepare_override_image(self, image_item, override_image_uuid):
        self.image = image_item
        self.os_image = self.get_image(override_image_uuid)
        self.image_name = self.os_image.name
        print("Found image %s (%s)" % (self.os_image.id, self.os_image.name))
        self.delete_image = False
        self.override_image = True  # refactor me
        self.image_was_removed = False

    def get_image(self, image):
        self.connect()
        return self.os.get_image(image)

    def prepare_key(self):
        self.key_name = self.make_test_name('key')
        self.os_key = None
        self.delete_keypair = True
        self.override_keypair = None
        self.keypair_was_removed = False

    def guess_flavor(self, tenv_item):
        self.connect()
        just_flavor = tenv_item.get('nova.flavor')
        flavor_id = tenv_item.get('nova.flavor_id')
        if flavor_id and just_flavor:
            raise FlavorError(
                "Found both flavor and flavor_id, this shouldn't happen"
            )
        if flavor_id:
            return self.os.get_flavor(flavor_id)
        elif just_flavor:
            return self.os.fuzzy_find_flavor(just_flavor)
        else:
            raise FlavorError("Neither flavor nor flavor_id is present")

    def prepare_instance(self, tenv_item, delete_instance_flag):
        self.userdata = self._userdata(tenv_item)
        self.instance_name = self.make_test_name('test')
        self.os_instance = None
        self.config_drive = tenv_item['nova'].get('config_drive', False)
        self.availability_zone = tenv_item['nova'].get(
            'availability_zone', None
        )
        self.delete_instance = delete_instance_flag
        self.nic_list = list(self.prepare_nics(tenv_item['nova']))
        self.main_nic_regexp = tenv_item['nova'].get('main_nic_regexp', None)
        self.override_instance = None
        self.instance_was_removed = False

    def _userdata(self, tenv_item):
        if 'nova.userdata' in tenv_item:
            return tenv_item['nova.userdata']
        elif 'nova.userdata_file' in tenv_item:
            return open(tenv_item['nova.userdata_file'], 'r').read()
        else:
            return None

    def connect(self):
        if not self.os:
            print("Connecting to Openstack")
            self.os = osclient.OSClient(
                keystone_data=self.test_environment['keystone'],
                nova_data=self.test_environment['nova'],
                glance_data=self.image.get('glance'),
                neutron_data=self.test_environment.get('neutron'),
                overrides=os.environ,
                ca_path=self.test_environment.get(
                    'ssl_ca_path',
                    '/etc/ssl/certs'
                ),
                insecure=self.test_environment.get('ssl_insecure', False),
                disable_warnings=self.test_environment.get('disable_warnings')
            )

    @staticmethod
    def prepare_nics(env):
        for nic in env.get('nics', []):
            response = {}
            if 'net_id' in nic:
                response['net-id'] = nic['net_id']
            # TODO add fixed IP/mac/etc
            yield response

    @staticmethod
    def make_test_name(bare_name):
        return 'DIBCTL-%s' % (str(uuid.uuid4()),)

    def init_keypair(self):
        with timeout.timeout(self.keypair_timeout):
            self.os_key = self.os.new_keypair(self.key_name)

    def upload_image(self, timeout_s):
        with timeout.timeout(timeout_s):
            if not self.override_image:
                filename = self.image['filename']
                disk_format = self.combined_glance_section.get(
                    'disk_format', 'qcow2')
                container_format = self.combined_glance_section.get(
                    'container_format', 'bare')
                min_disk = self.combined_glance_section.get(
                    'min_disk', 0)
                min_ram = self.combined_glance_section.get(
                    'min_ram', 0)
                protected = self.combined_glance_section.get(
                    'protected', False
                )
                print("Uploading image from %s (time limit is %s s)" % (
                    filename, timeout_s
                ))
                self.os_image = self.os.upload_image(
                    self.image_name,
                    filename,
                    disk_format=disk_format,
                    container_format=container_format,
                    min_disk=min_disk,
                    min_ram=min_ram,
                    protected=protected,
                    meta=self.image['glance'].get('properties', {})
                )
                print("Image %s uploaded." % self.os_image.id)

    def spawn_instance(self, timeout_s):
        print("Creating test instance (time limit is %s s)" % timeout_s)
        flavor = self.guess_flavor(self.test_environment)
        self.flavor = flavor
        with timeout.timeout(timeout_s):
            self.os_instance = self.os.boot_instance(
                name=self.instance_name,
                image_uuid=self.os_image,
                flavor=flavor,
                key_name=self.os_key.name,
                nic_list=self.nic_list,
                config_drive=self.config_drive,
                userdata=self.userdata,
                availability_zone=self.availability_zone
            )
            print("Instance %s created." % self.os_instance.id)

    def get_instance_main_ip(self):
        self.ip = self.os.get_instance_ip(
            self.os_instance,
            self.main_nic_regexp
        )
        return self.ip

    def get_image_info(self):
        self.image_info = self.get_image(
            self.os_instance.image['id']
        )
        return self.image_info

    def wait_for_instance(self, timeout_s):
        print(
            "Waiting for instance to become active (time limit is %s s)" %
            timeout_s
        )
        with timeout.timeout(timeout_s):
            while self.os_instance.status != 'ACTIVE':
                if self.os_instance.status in ('ERROR', 'DELETED'):
                    raise InstanceError(
                        "Instance %s state is '%s' (expected 'ACTIVE'). "
                        "Error message is: %s" % (
                            self.os_instance.id,
                            self.os_instance.status,
                            self.os_instance.fault.get('message', 'no message')
                        )
                    )
                time.sleep(self.SLEEP_DELAY)
                self.os_instance = self.os.get_instance(self.os_instance.id)
        print("Instance become active.")

    def prepare_ssh(self):
        ssh_item = self.image.get('tests.ssh')
        if ssh_item and self.ip:
            self.ssh = ssh.SSH(
                ip=self.ip,
                username=ssh_item['username'],
                private_key=self.os_key.private_key,
                port=ssh_item.get('port', 22)
            )

    def prepare(self):
        self.init_keypair()
        sys.stdout.flush()
        self.upload_image(self.upload_timeout)
        sys.stdout.flush()
        self.spawn_instance(self.create_timeout)
        sys.stdout.flush()
        self.wait_for_instance(self.active_timeout)
        sys.stdout.flush()
        self.get_instance_main_ip()
        sys.stdout.flush()
        self.prepare_ssh()
        sys.stdout.flush()

    @staticmethod
    def _cleanup(name, obj, flag, call):
        try:
            if obj:
                if flag:
                    print("Removing %s." % name)
                    call(obj)
                else:
                    print("Not removing %s." % name)
        except Exception as e:
            print("Error while clear up %s: %s" % (name, e))

    def cleanup_instance(self):
        self._cleanup(
            'instance',
            obj=self.os_instance,
            flag=self.delete_instance,
            call=self.os.delete_instance
        )

    def cleanup_image(self):
        self._cleanup(
            'image',
            obj=self.os_image,
            flag=self.delete_image,
            call=self.os.delete_image
        )

    def cleanup_ssh_key(self):
        self._cleanup(
            'ssh key',
            obj=self.os_key,
            flag=self.delete_keypair,
            call=self.os.delete_keypair
        )
        if self.ssh:
            if self.delete_keypair:
                del self.ssh
                self.ssh = None
            else:
                name = self.ssh.keep_key_file()
                print("SSH private key is in %s" % name)

    def cleanup(self):
        print("\nClearing up...")
        self.cleanup_instance()
        self.cleanup_ssh_key()
        self.cleanup_image()
        print("\nClearing done\n")

    def report_if_fail(self):
        if self.report and self.os_instance and not self.delete_instance:
            print(
                "Instance %s is not removed. "
                "Please debug and remove it manually." % self.os_instance.id
            )
            print("Instance ip is %s" % self.ip)
            # print("Private key file is %s" % self.os_key_private_file)
            # A problem. Should fix this
        if (
            self.report
            and self.os_image
            and not self.delete_image
            and not self.override_image
        ):
            print(
                "Image %s is not removed. "
                "Please debug and remove it manually." % self.os_image.id
            )

    def __enter__(self):
        self.connect()
        try:
            self.prepare()
            return self
        except BaseException as e:
            if not isinstance(e, TimeoutError):
                print("Exception while preparing instance for test: %s" % e)
                print("Will print full trace after cleanup")
                self.cleanup()
                print("Continue tracing on original error: %s" % e)
            raise

    def __exit__(self, e_type, e_val, e_tb):
        "Cleaning up on exit"
        self.cleanup()
        # self.report_if_fail()

    def get_env_config(self):
        env = {
            'instance_uuid': str(self.os_instance.id),
            'instance_name': str(self.instance_name).lower(),
            'flavor_id': str(self.flavor.id),
            'main_ip': str(self.ip),
            # 'ssh_private_key': str(self.os_key_private_file),  REFACTOR!
            'flavor_ram': str(self.flavor.ram),
            'flavor_name': str(self.flavor.name),
            'flavor_vcpus': str(self.flavor.vcpus),
            'flavor_disk': str(self.flavor.disk)
        }
        for num, ip in enumerate(self.ips()):
            env.update({'ip_' + str(num + 1): str(ip)})
        for num, iface in enumerate(self.network()):
            env.update(
                {'iface_' + str(num + 1) + '_info': json.dumps(iface._info)}
            )
        for meta_name, meta_value in self.flavor.get_keys().items():
            env.update({'flavor_meta_' + str(meta_name): str(meta_value)})
        return env

    def ips(self):
        result = []
        for ips in self.os_instance.networks.values():
            result.extend(ips)
        return result

    def ips_by_version(self, version=4):
        result = []
        for ip in self.ips():
            # Convert string to unicode object in Python 2.x
            if sys.version_info < (3, 0):
                ip = unicode(ip)
            ipaddr = ipaddress.ip_address(ip)
            if ipaddr.version == version:
                result.append(str(ip))
        return result

    def network(self):
        return self.os_instance.interface_list()

    def wait_for_port(self, port=22, timeout=60):
        '''check if we can connect to given port. Wait for port
           up to timeout and then return error
        '''
        print(
            "Waiting for instance to accept connections on %s:%s "
            "(time limit is %s s)" % (self.ip, port, timeout)
        )
        start = time.time()
        while (start + timeout > time.time()):
            # add source IP support here
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((self.ip, port))
            if result == 0:
                # time.sleep(1)   # in many cases there is a race between port
                # become availabe and actual service been available
                print("Instance accepts connections on port %s" % port)
                return True
            time.sleep(3)
        print(
            "Instance is not accepting connection on ip %s port %s." % (
                self.ip, port
            )
        )
        return False

    def update_image_delete_status(self, delete=True):
        if delete:
            if self.override_image:
                self.delete_image = True
            else:
                print("Will not delete image as it was not uploaded by us")
        if not delete:
            self.delete_image = False

    def update_instance_delete_status(self, delete=True):
        if delete:
            if self.override_instance:
                self.delete_instance = True
            else:
                print("Will not delete instance as it was not created by us")
        if not delete:
            self.delete_instance = False

    def update_keypair_delete_status(self, delete=True):
        if delete:
            if self.override_keypair:
                self.delete_keypair = True
            else:
                print("Will not delete keypair as it was not created by us")
        if not delete:
            self.delete_keypair = False

    def instance_status(self):
        return {
            "preexisted": bool(self.override_instance),
            "was_removed": bool(self.instance_was_removed),
            "deletable": bool(self.delete_instance),
            "id": self.os_instance.id,
            "name": self.instance_name
        }

    def image_status(self):
        return {
            "preexisted": bool(self.override_image),
            "was_removed": bool(self.image_was_removed),
            "deletable": bool(self.delete_image),
            "id": self.os_image.id,
            "name": self.image_name
        }

    def keypair_status(self):
        ''' return value (is_created_by_us, was_removed, will_be_removed)'''
        return {
            "preexisted": bool(self.override_keypair),
            "was_removed": self.keypair_was_removed,
            "deletable": self.delete_keypair,
            "id": self.os_key.id,
            "name": self.os_key.name  # doubious
        }
