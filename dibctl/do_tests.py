import prepare_os
import pytest_runner
import shell_runner
import ssh

class TestError(EnvironmentError):
    pass


class UnsupportedRunnerError(TestError):
    pass


class BadTestConfigError(TestError):
    pass


class DoTests(object):
    DEFAULT_PORT_WAIT_TIMEOUT = 61
    DEFAULT_PORT = 22

    def __init__(
        self,
        image,
        test_env,
        image_uuid=None,
        upload_only=False,
        continue_on_fail=False,
        keep_failed_image=False,
        keep_failed_instance=False,
        shell_on_errors=False
    ):
        '''
            - image - entry of images.yaml
            - env - environment to use (entry of test_environments.yaml)
            - image_uuid - override image-related things
            - upload_only - don't run tests
        '''
        self.shell_on_errors = shell_on_errors
        self.keep_failed_image = keep_failed_image
        self.keep_failed_instance = keep_failed_instance
        self.continue_on_fail = continue_on_fail
        self.image = image
        self.ssh = None
        self.override_image_uuid = image_uuid
        if image_uuid:
            self.delete_image = False
        else:
            self.delete_image = True
        if 'tests' in image:
            self.tests_list = image['tests']['tests_list']
            self.environment_variables = image['tests'].get('environment_variables', None)
        else:
            self.tests_list = []
        self.test_env = test_env

    def check_if_keep_stuff_after_fail(self, prep_os):
        if self.keep_failed_instance:
            prep_os.delete_instance = False
            prep_os.delete_keypair = False
            prep_os.report = True
            print("Do not delete instance for failed tests")
        if self.keep_failed_image:
            prep_os.delete_image = False
            print("Do not delete image for failed tests")

    @staticmethod
    def get_runner(test):
        RUNNERS = {
            'pytest': pytest_runner.runner,
            'shell': shell_runner.runner
        }
        found = False
        for runner_name, runner_func in RUNNERS.iteritems():
            if runner_name in test:
                if found:
                    raise BadTestConfigError("Duplicate runner name in  %s" % str(test))
                name = runner_name
                runner = runner_func
                path = test[runner_name]
                found = True
        if not found:
            raise BadTestConfigError("No known runner names found in %s" % str(test))
        return name, runner, path

    def run_test(self, test, instance_config, vars):
        runner_name, runner, path = self.get_runner(test)
        print("Running tests %s: %s." % (runner_name, path))
        timeout_val = test.get('timeout', 300)
        if runner(path, self.ssh, instance_config, vars, timeout_val=timeout_val, continue_on_fail=self.continue_on_fail):
            print("Done running tests  %s: %s." % (runner_name, path))
            return True
        else:
            print("Some %s: %s tests have failed." % (runner_name, path))
            if self.continue_on_fail:
                print("Continue testing.")
                return True
            else:
                print("Stop testing due to previous error.")
                return False

    def run_all_tests(self):
        was_error = False
        print("Will run test instance with flavor %s." % (
            self.test_env['nova']["flavor"]
        ))
        with prepare_os.PrepOS(
            self.image,
            self.test_env,
            override_image=self.override_image_uuid,
            delete_image=self.delete_image
        ) as prep_os:
            if 'ssh' in self.image:
                self.ssh = ssh.SSH(prep_os.ip, self.image['ssh'].get('username', 'user'), prep_os.os_key, self.image['ssh'].get('port', 22))
            else:
                self.ssh = None
            port = self.image['tests'].get('wait_for_port', self.DEFAULT_PORT)
            port_wait_timeout = self.image['tests'].get('port_wait_timeout', self.DEFAULT_PORT_WAIT_TIMEOUT)
            if port:
                port_available = prep_os.wait_for_port(port, port_wait_timeout)
                if not port_available:
                    self.check_if_keep_stuff_after_fail(prep_os)
                    was_error = True
                    raise TestError("Timeout while waiting instance to accept connection on port %s." % port)
            for test in self.tests_list:
                if self.run_test(test, prep_os, self.environment_variables) is not True:
                    self.check_if_keep_stuff_after_fail(prep_os)
                    was_error = True
                    break
            if was_error:
                print("ERROR: Some tests failed.")
                if self.shell_on_errors:
                    self.open_shell()
                return False
            else:
                print("Done all tests successfully.")
                return True

    def open_shell(self):
        if 'ssh' not in self.image:
            raise TestError('Asked to open ssh after test failed, but there is no ssh section in image config')
        raise NotImplementedError("Option is not implemented yet")
