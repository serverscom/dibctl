import prepare_os
import pytest_runner
import shell_runner
import config
import os


class TestError(EnvironmentError):
    pass


class UnsupportedRunnerError(TestError):
    pass


class BadTestConfigError(TestError):
    pass


class DoTests(object):
    DEFAULT_PORT_WAIT_TIMEOUT = 61
    # DEFAULT_PORT = 22

    def __init__(
        self,
        image,
        test_env,
        image_uuid=None,
        upload_only=False,
        continue_on_fail=False,
        keep_failed_image=False,
        keep_failed_instance=False
    ):
        '''
            - image - entry of images.yaml
            - env - environment to use (entry of test_environments.yaml)
            - image_uuid - override image-related things
            - upload_only - don't run tests
        '''
        self.keep_failed_image = keep_failed_image
        self.keep_failed_instance = keep_failed_instance
        self.continue_on_fail = continue_on_fail
        self.image = image
        self.override_image_uuid = image_uuid
        if image_uuid:
            self.delete_image = False
        else:
            self.delete_image = True
        self.tests_list = image.get('tests.tests_list', [])
        self.environment_variables = image.get('tests.environment_variables', None)
        self.test_env = test_env

    def check_if_keep_stuff_after_fail(self, prep_os):
        if self.keep_failed_instance:
            prep_os.update_instance_delete_status(delete=False)
            prep_os.update_keypair_delete_status(delete=False)
        if self.keep_failed_image:
            prep_os.update_image_delete_status(delete=False)
        self.report(prep_os)

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

    def run_test(self, ssh, test, instance_config, vars):
        runner_name, runner, path = self.get_runner(test)
        print("Running tests %s: %s." % (runner_name, path))
        timeout_val = test.get('timeout', 300)
        if runner(
            path,
            ssh,
            instance_config,
            vars,
            timeout_val=timeout_val,
            continue_on_fail=self.continue_on_fail
        ):
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

    def run_all_tests(self, prep_os):
        success = True

        for test in self.tests_list:
            if self.run_test(self.ssh, test, prep_os, self.environment_variables) is not True:
                self.check_if_keep_stuff_after_fail(prep_os)
                success = False
                break
        return success

    def init_ssh(self, prep_os):
        if 'ssh' in self.image['tests']:
            self.ssh = prep_os.ssh  # continue refactoring this!

    def wait_port(self, prep_os):
        if 'wait_for_port' in self.image['tests']:
            port = self.image['tests']['wait_for_port']
            port_wait_timeout = config.get_max(
                        self.image,
                        self.test_env,
                        'tests.port_wait_timeout',
                        self.DEFAULT_PORT_WAIT_TIMEOUT
                    )
            port_available = prep_os.wait_for_port(port, port_wait_timeout)
            if not port_available:
                self.check_if_keep_stuff_after_fail(prep_os)
                raise TestError("Timeout while waiting instance to accept connection on port %s." % port)
            return True
        else:
            return False

    def process(self, shell_only, shell_on_errors):
        prep_os = prepare_os.PrepOS(
            self.image,
            self.test_env,
            override_image=self.override_image_uuid,
            delete_image=self.delete_image
        )
        with prep_os:
            self.init_ssh(prep_os)
            self.wait_port(prep_os)
            if shell_only:
                result = self.open_shell(
                    prep_os.ssh,
                    'Opening ssh shell to instance without running tests'
                )
                self.check_if_keep_stuff_after_fail(prep_os)
                return result
            result = self.run_all_tests(prep_os)
            if not result:
                print("Some tests failed")
                if shell_on_errors:
                    self.open_shell(prep_os.ssh, 'There was an test error and asked to open --shell')
                    self.check_if_keep_stuff_after_fail(prep_os)
                    return result
            else:
                print("All tests passed successfully.")
            return result

    def open_shell(self, ssh, reason):
        if not ssh:
            raise TestError('Asked to open ssh shell to server, but there is no ssh section in the image config')
        message = reason + '\nUse "exit 42" to keep instance\n'
        status = ssh.shell({}, os.environ, message)
        if status == 42:  # magical constant!
            self.keep_failed_instance = True
        return status

    @staticmethod
    def report_item(onthologic_name, item):
        if not item["was_removed"] and not item['preexisted'] and not item['deletable']:
            print("%s: %s (%s), will not be removed" % (onthologic_name, item['id'], item['name']))

    @staticmethod
    def report_ssh(ssh):
        if ssh:
            print("You may use following line to access server")
            print(" ".join(ssh.command_line()))

    def report(self, prep_os):
        image_status = prep_os.image_status()
        instance_status = prep_os.instance_status()
        keypair_status = prep_os.keypair_status()
        self.report_item("Keypair", keypair_status)
        self.report_item("Image", image_status)
        self.report_item("Instance", instance_status)
        if not instance_status['was_removed'] and not instance_status['deletable']:
            self.report_ssh(prep_os.ssh)

    def reconfigure_for_existing_instance(self, instance, private_key_file=None):
        raise NotImplementedError
