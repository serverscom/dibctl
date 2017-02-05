import osclient
import timeout
import sys
import uuid
import socket
import time
import os
import json
import tempfile


class TimeoutError(EnvironmentError):
    pass


class InstanceError(EnvironmentError):
    pass


class PrepOS(object):

    'Provides test-specific image/instance/keypair with timeouts and cleanup at errors'
    LONG_OS_TIMEOUT = 360
    SHORT_OS_TIMEOUT = 10
    SLEEP_DELAY = 3

    def __init__(self, image, test_environment, override_image=None, delete_image=True, delete_instance=True):
        self.report = True
        self.override_image = override_image
        if override_image:
            self.image_name = ""
            self.delete_image = False
            self.upload_timeout = self.LONG_OS_TIMEOUT
        else:
            self.image_name = self.make_test_name(image['glance']['name'])
            self.image = image
            self.delete_image = delete_image
            self.upload_timeout = self.image['glance'].get('upload_timeout', self.LONG_OS_TIMEOUT)
        self.key_name = self.make_test_name('key')
        self.instance_name = self.make_test_name('test')
        self.os_image = None
        self.os_instance = None
        self.os_key = None
        self.delete_keypair = True
        self.config_drive = test_environment.get('config_drive')

        self.delete_instance = delete_instance
        self.flavor_id = test_environment['nova']['flavor']
        self.nic_list = list(self.prepare_nics(test_environment))
        self.main_nic_regexp = test_environment.get('main_nic_regexp', None)
        self.os = osclient.OSClient(
            keystone_data=test_environment['keystone'],
            nova_data=test_environment['nova'],
            glance_data=osclient.smart_join_glance_config(
                test_environment.get('glance', {}),
                self.image.get('glance', {})
            ),
            neutron_data=test_environment.get('neutron', None),
            overrides=os.environ,
            ca_path=test_environment.get('ssl_ca_path', '/etc/ssl/certs'),
            insecure=test_environment.get('ssl_insecure', False)
        )

    @staticmethod
    def prepare_nics(env):
        for nic in env.get('nics', []):
            yield {'net-id': nic}

    @staticmethod
    def make_test_name(bare_name):
        return 'DIBCTL-%s-%s' % (bare_name, str(uuid.uuid4()))

    def init_keypair(self):
        with timeout.timeout(self.SHORT_OS_TIMEOUT, self.error_handler):
            self.os_key = self.os.new_keypair(self.key_name)

    def save_private_key(self):
        f = tempfile.NamedTemporaryFile(prefix='DIBCTL_ssh_key', suffix='private', delete=False)
        f.write(self.os_key.private_key)
        f.close()
        self.os_key_private_file = f.name

    def wipe_private_key(self):
        with open(self.os_key_private_file, 'w') as f:
            f.write(' ' * 4096)
        os.remove(self.os_key_private_file)

    def upload_image(self, timeout_s):
        with timeout.timeout(timeout_s, self.error_handler):
            if not self.override_image:
                filename = self.image['filename']
                print("Uploading image from %s (time limit is %s s)" % (filename, timeout_s))
                self.os_image = self.os.upload_image(
                    self.image_name,
                    filename,
                    meta=self.image['glance'].get('properties', {})
                )
                print("Image %s uploaded." % self.os_image)
            else:
                self.os_image = self.os.get_image(self.override_image)

    def spawn_instance(self, timeout_s):
        print("Creating test instance (time limit is %s s)" % timeout_s)
        with timeout.timeout(timeout_s, self.error_handler):
            self.os_instance = self.os.boot_instance(
                self.instance_name,
                self.os_image,
                self.flavor_id,
                self.os_key.name,
                self.nic_list,
                self.config_drive
            )
            print("Instance %s created." % self.os_instance.id)

    def get_instance_main_ip(self):
        self.ip = self.os.get_instance_ip(self.os_instance, self.main_nic_regexp)
        return self.ip

    def wait_for_instance(self, timeout_s):
        print("Waiting for instance to become active (time limit is %s s)" % timeout_s)
        with timeout.timeout(timeout_s, self.error_handler):
            while self.os_instance.status != 'ACTIVE':
                if self.os_instance.status in ('ERROR', 'DELETED'):
                    raise InstanceError(
                        "Instance %s got %s state." % (
                            self.os_instance,
                            self.os_instance.status
                        )
                    )
                time.sleep(self.SLEEP_DELAY)
                self.os_instance = self.os.get_instance(self.os_instance.id)
        print("Instance become active.")

    def prepare(self):
        self.init_keypair()
        self.save_private_key()
        sys.stdout.flush()
        self.upload_image(self.upload_timeout)
        sys.stdout.flush()
        self.spawn_instance(self.SHORT_OS_TIMEOUT)
        sys.stdout.flush()
        self.wait_for_instance(self.LONG_OS_TIMEOUT)
        sys.stdout.flush()
        self.get_instance_main_ip()
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
            self.os_instance,
            self.delete_instance,
            self.os.delete_instance
        )

    def cleanup_image(self):
        self._cleanup(
            'image',
            self.os_image,
            self.delete_image,
            self.os.delete_image
        )

    def cleanup_ssh_key(self):
        self._cleanup(
            'ssh key',
            self.os_key,
            self.delete_keypair,
            self.os.delete_keypair
        )
        try:
            if self.delete_keypair and self.delete_instance:
                self.wipe_private_key()
        except Exception as e:
            print("Error while clear up ssh key file: %s" % e)

    def cleanup(self):
        print("\nClearing up...")
        self.cleanup_instance()
        self.cleanup_ssh_key()
        self.cleanup_image()
        print("\nClearing done\n")

    def error_handler(self, signum, frame, timeout=True):
        if timeout:
            print("Timeout!")
        print("Clearing up due to error")
        self.cleanup()
        if timeout:
            raise TimeoutError("Timeout")

    def report_if_fail(self):
        if self.report and self.os_instance and not self.delete_instance:
            print("Instance %s is not removed. Please debug and remove it manually." % self.os_instance.id)
            print("Instance ip is %s" % self.ip)
            print("Private key file is %s" % self.os_key_private_file)

    def __enter__(self):
        try:
            self.prepare()
            return self
        except Exception as e:
            print("Exception while preparing instance for test: %s" % e)
            print("Will print full trace after cleanup")
            self.cleanup()
            print("Continue tracing on original error: %s" % e)
            raise

    def __exit__(self, e_type, e_val, e_tb):
        "Cleaning up on exit"
        self.cleanup()
        self.report_if_fail()

    def get_env_config(self):
        flavor = self.flavor()
        env = {
            'instance_uuid': str(self.os_instance.id),
            'instance_name': str(self.instance_name).lower(),
            'flavor_id': str(self.flavor_id),
            'main_ip': str(self.ip),
            'ssh_private_key': str(self.os_key_private_file),
            'flavor_ram': str(flavor.ram),
            'flavor_name': str(flavor.name),
            'flavor_vcpus': str(flavor.vcpus),
            'flavor_disk': str(flavor.disk)
        }
        for num, ip in enumerate(self.ips()):
            env.update({'ip_' + str(num + 1): str(ip)})
        for num, iface in enumerate(self.network()):
            env.update({'iface_' + str(num + 1) + '_info': json.dumps(iface._info)})
        for meta_name, meta_value in flavor.get_keys().items():
            env.update({'flavor_meta_' + str(meta_name): str(meta_value)})
        return env

    def flavor(self):
        return self.os.get_flavor(self.flavor_id)

    def ips(self):
        result = []
        for ips in self.os_instance.networks.values():
            result.extend(ips)
        return result

    def network(self):
        return self.os_instance.interface_list()

    def wait_for_port(self, port=22, timeout=60):
        '''check if we can connect to given port. Wait for port
           up to timeout and then return error
        '''
        print("Waiting for instance to accept connections on %s:%s" % (self.ip, port))
        start = time.time()
        while (start + timeout > time.time()):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # add source IP
            result = sock.connect_ex((self.ip, port))
            if result == 0:
                time.sleep(1)   # in many cases there is a race between port
                # become availabe and actual service been available
                print("Instance accepts connections on port %s" % port)
                return True
            time.sleep(3)
        print("Instance is not accepting connection on ip %s port %s." % (self.ip, port))
        return False
