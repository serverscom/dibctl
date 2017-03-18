import argparse
import config
import os
import dib
import sys
import osclient
import do_tests
import prepare_os
import version
from keystoneauth1 import exceptions as keystone_exceptions


class PrematureExitError(SystemExit):
    pass


class NoTestsError(PrematureExitError):
    pass


class TestEnvironmentNotFoundError(PrematureExitError):
    pass


class NotFoundInConfigError(PrematureExitError):
    pass


class GenericCommand(object):
    # An abstract class, shouldn't be used directly
    options = []
    # Possible values:
    # 'input',
    # 'output',
    # 'img-config',
    # 'upload-confg',
    # 'test-env-config',
    # 'imagelabel',
    # 'uploadlabel',
    name = 'generic'
    help = 'replace me'
    image = None

    def __init__(self, subparser):
        self.parser = subparser.add_parser(self.name, help=self.help)
        self.parser.add_argument('--debug', help='Display this message', action='store_true', default=False)
        self.parser.add_argument('--version', help='Display version', action='version', version=version.VERSION_STRING)
        if 'input' in self.options:
            self.parser.add_argument(
                '--input', '-i',
                help='Input filename for image (overrides default)',
                dest='filename'
            )
        if 'output' in self.options:
            self.parser.add_argument(
                '--output', '-o',
                help='Outut filename for image (overrides default)',
                dest='filename'
            )
        if 'img-config' in self.options:
            self.parser.add_argument('--images-config', help='Use specific file instead of images.yaml')
        if 'upload-config' in self.options:
            self.parser.add_argument('--upload-config', help='Use specific file instead of upload.yaml')
        if 'test-env-config' in self.options:
            self.parser.add_argument('--test-config', help='Name of custom test.yaml')
        if 'imagelabel' in self.options:
            self.parser.add_argument('imagelabel', help='Label of image in the images.yaml')
        if 'uploadlabel' in self.options:
            self.parser.add_argument('envlabel', help='Use given environment from upload.yaml')
        self.add_options()
        self.parser.set_defaults(command=self.command)

    def command(self, args):
        self.args = args
        if 'img-config' in self.options:
            self.image_config = config.ImageConfig(
                config_file=self.args.images_config,
                override_filename=self.args.filename
            )
        if 'upload-config' in self.options:
            self.upload_config = config.UploadEnvConfig(
                config_file=self.args.upload_config
            )
        if 'test-env-config' in self.options:
            self.test_env_config = config.TestEnvConfig(
                config_file=self.args.test_config
            )
        if 'imagelabel' in self.options:
            self.image = self.image_config[self.args.imagelabel]
        if 'uploadlabel' in self.options:
            self.upload_env = self.upload_config[self.args.envlabel]
            glance_data = osclient.smart_join_glance_config(
                {'name': 'foo'},
                {}
            )
            self.os = osclient.OSClient(
                keystone_data=self.upload_env['keystone'],
                nova_data={},
                glance_data=glance_data,
                neutron_data={},
                overrides=os.environ,
                ca_path=self.upload_env.get('ssl_ca_path', '/etc/ssl/cacerts'),
                insecure=self.upload_env.get('ssl_insecure', False),
                disable_warnings=self.upload_env.get('disable_warnings', False)
            )
        return self._command()

    def _command(self):
        raise NotImplementedError("Should be redefined")

    def add_options(self):
        pass  # not implemented in the abstract class


class BuildCommand(GenericCommand):
    name = 'build'
    help = 'Build image'
    options = ['imagelabel', 'output', 'img-config']

    def _prepare(self):
        dib_section = self.image['dib']
        dib.validate_version(self.image.get('dib.min_version'), self.image.get('dib.max_version'))
        self.dib = dib.DIB(
            self.image['filename'],
            dib_section['elements'],
            additional_options=dib_section.get('cli_options', []),
            env=dib_section.get('environment_variables', {})
        )

    def _run(self):
        code = self.dib.run()
        if code != 0:
            print("Error: Failed to build image '%s', exit code is %s" % (self.args.imagelabel, code))
        else:
            print("Image %s build successfully into file %s" % (self.args.imagelabel, self.image['filename']))
        return code

    def _command(self):
        self._prepare()
        return self._run()


class TestCommand(GenericCommand):
    name = 'test'
    help = 'Test image'
    options = ['imagelabel', 'input', 'img-config', 'test-env-config']

    def add_options(self):
        self.parser.add_argument(
            '--environment',
            dest='envlabel',
            help='Use given environment for tests (override label from images.yaml)'
        )
        self.parser.add_argument(
            '--upload-only',
            action='store_true',
            help='Do not run tests, only upload image to test env'
        )
        self.parser.add_argument(
            '--use-existing-image',
            help='Skip upload and use given image uuid for test (will not be removed after test)',
            dest='uuid'
        )
        self.parser.add_argument(
            '--use-existing-instance',
            help='Skip upload/boot and use given instance for test (will not be removed after test)',
            dest='instance'
        )
        self.parser.add_argument(
            '--private-key-file',
            help='Use private key file for tests (existing instance only)',
            dest='private_key_file'
        )
        self.parser.add_argument(
            '--keep-failed-image',
            action='store_true',
            help="Do not remove image if test failed"
        )
        self.parser.add_argument(
            '--keep-failed-instance',
            action='store_true',
            help="Do not remove instance and ssh key is test failed"
        )
        self.parser.add_argument(
            '--shell',
            action='store_true',
            help="Open ssh shell to the server if some test failed and there is ssh config for image"
        )
        self.parser.add_argument(
            '--shell-only',
            action='store_true',
            help='Run ssh shell to instance directly, skipping tests'
        )

    def _prepare(self):
        tests = self.image.get('tests', None)
        if not tests:
            raise NoTestsError(
                'No tests section was defined for image %s in the image config. Abort.' % self.args.imagelabel
            )
        env_label = self.args.envlabel or tests.get('environment_name', None)
        if not env_label:
            raise TestEnvironmentNotFoundError('No environemnt name for tests were no given in config or command line')
        self.test_env = self.test_env_config[env_label]

    def _command(self):
        self._prepare()
        dt = do_tests.DoTests(
            self.image,
            test_env=self.test_env,
            image_uuid=self.args.uuid,
            upload_only=self.args.upload_only,
            keep_failed_image=self.args.keep_failed_image,
            keep_failed_instance=self.args.keep_failed_instance
        )
        if self.args.instance:
            dt.reconfigure_for_existing_instance(self.args.instance, self.args.private_key_file)
        try:
            status = dt.process(shell_only=self.args.shell_only, shell_on_errors=self.args.shell)
        except do_tests.TestError as e:
            print("Error while testing: %s" % e)
            return 1
        if status:
            return 0
        else:
            return 1


class UploadCommand(GenericCommand):
    name = 'upload'
    help = 'Upload image'
    options = ['imagelabel', 'input', 'img-config', 'upload-config', 'uploadlabel']

    def add_options(self):
        self.parser.add_argument('--no-obsolete', action='store_true', help='Do not obsolete images with same name')

    def _prepare(self):
        try:
            self.glance_info = self.image['glance']
        except KeyError as e:
            raise NotFoundInConfigError("Glance section not found int the image config")
        self.name = self.glance_info['name']
        self.meta = self.glance_info.get('properties', {})
        self.filename = self.image['filename']
        self.public = self.glance_info.get('public', False)

    def upload_to_glance(self):
        self.image = self.os.upload_image(
            self.name,
            self.filename,
            self.public,
            meta=self.meta
        )
        print("Image ''%s' uploaded with uuid %s" % (self.image.name, self.image.id))

    def obsolete_old_images(self):
        candidates = self.os.older_images(self.name, self.image.id)
        for img in candidates:
            obsolete_image = self.os.mark_image_obsolete(self.name, img)
            print("Obsoleting %s" % obsolete_image.id)

    def _command(self):
        self._prepare()
        self.upload_to_glance()
        if not self.args.no_obsolete:
            self.obsolete_old_images()


class RotateCommand(GenericCommand):
    name = 'rotate'
    help = 'Remove unused obsolete images'
    options = ['upload-config', 'uploadlabel']

    def _command(self):
        pass


class ObsoleteCommand(GenericCommand):
    name = 'mark-obsolete'
    help = 'Obsolete image'
    options = ['upload-config', 'uploadlabel']

    def add_options(self):
        self.parser.add_argument('uuid', help="image UUID to mark as obsolete")

    def _command(self):
        img = self.os.get_image(self.args.uuid)
        self.os.mark_image_obsolete(img.name, img)
        print("Obsoleting %s (%s)" % (img.id, img.name))


class TransferCommand(GenericCommand):
    name = 'transfer'
    help = 'Transfer image from one openstack to another'
    options = []

    def add_options(self):
        self.parser.add_argument('uuid', help="image UUID to transfer")
        self.parser.add_argument('--src-auth-url', help="OS_AUTH_URL for the source openstack")
        self.parser.add_argument('--dst-auth-url', help="OS_AUTH_URL for the destination openstack")
        self.parser.add_argument('--src-tenant-name', help="OS_TENANT_NAME for the source openstack")
        self.parser.add_argument('--dst-tenant-name', help="OS_TENANT_NAME for the destination openstack")
        self.parser.add_argument('--src-username', help="OS_USERNAME for the source openstack")
        self.parser.add_argument('--dst-username', help="OS_USERNAME for the destination openstack")
        self.parser.add_argument('--src-password', help="OS_PASSWORD for the source openstack")
        self.parser.add_argument('--dst-password', help="OS_PASSWORD for the destination openstack")
        self.parser.add_argument('--ignore-meta', action="store_true", help="Do not copy metada")
        self.parser.add_argument(
            '--ignore-membership',
            action="store_true",
            help="Do not copy membership for shared images"
        )

    def _command(self):
        pass


class ValidateCommand(GenericCommand):
    name = 'validate'
    help = 'Validate configuration files against config schema'
    options = ['upload-config', 'img-config', 'test-env-config', 'input']

    def _command(self):
        print("Configs have been validated.")
        return 0


class Main(object):
    def __init__(self, command_line=None):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('--debug', help='Display this message', action='store_true', default=False)
        self.parser.add_argument('--version', help='Display version', action='version', version=version.VERSION_STRING)
        subparsers = self.parser.add_subparsers(title='commands')
        BuildCommand(subparsers)
        TestCommand(subparsers)
        UploadCommand(subparsers)
        RotateCommand(subparsers)
        ObsoleteCommand(subparsers)
        TransferCommand(subparsers)
        ValidateCommand(subparsers)
        self.args = self.parser.parse_args(command_line)

    def run(self):
        command = self.args.command
        return command(self.args)


def main(line=None):
    m = Main(line)
    try:
        code = m.run()
    except (
        PrematureExitError,
        osclient.CredNotFound,
        osclient.OpenStackError,
        config.ConfigError,
        prepare_os.InstanceError,
        keystone_exceptions.ClientException,
        IOError
    ) as e:
        print("Error: %s" % str(e))
        code = -1
    sys.exit(code)


def init():
    if __name__ == "__main__":
        main()


init()
