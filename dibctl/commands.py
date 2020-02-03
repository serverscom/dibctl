import argparse
from . import config
import os
from . import dib
import sys
from . import osclient
from . import do_tests
from . import prepare_os
from . import version
from . import image_preprocessing
from keystoneauth1 import exceptions as keystone_exceptions
from novaclient import exceptions as novaclient_exceptions
from glanceclient import exc as glanceclient_exceptions


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
        else:
            self.image = {}
        if 'uploadlabel' in self.options:
            self.upload_env = self.upload_config[self.args.envlabel]
            self.glance_data = osclient.smart_join_glance_config(
                self.image.get('glance', {}),
                self.upload_env.get('glance', {})
            )
            self.os = osclient.OSClient(
                keystone_data=self.upload_env['keystone'],
                nova_data={},
                glance_data=self.glance_data,
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

    def _prepare(self):
        tests = self.image.get('tests', None)
        if not tests:
            raise NoTestsError(
                'No tests section was defined for image %s in the image config. Abort.' % self.args.imagelabel
            )
        env_label = self.args.envlabel or tests.get('environment_name', None)
        if not env_label:
            raise TestEnvironmentNotFoundError('No environment name for tests were no given in config or command line')
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
            dt.reconfigure_for_existing_instance(
                self.args.instance,
                self.args.private_key_file
            )
        status = dt.process(shell_only=False, shell_on_errors=self.args.shell)
        if status:
            return 0
        else:
            return 80


class ShellCommand(GenericCommand):
    name = 'shell'
    help = 'Open shell to test instance'
    options = ['imagelabel', 'input', 'img-config', 'test-env-config']

    def add_options(self):
        self.parser.add_argument(
            '--environment',
            dest='envlabel',
            help='Use given environment for tests (override label from images.yaml)'
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

    def _prepare(self):
        env_label = self.image.get(
            'tests.environment_name', self.args.envlabel)
        if not env_label:
            raise TestEnvironmentNotFoundError(
                'No environemnt name for tests were no given '
                'in config or command line'
            )
        self.test_env = self.test_env_config[env_label]

    def _command(self):
        self._prepare()
        dt = do_tests.DoTests(
            self.image,
            test_env=self.test_env,
            image_uuid=self.args.uuid,
            upload_only=False,
            keep_failed_image=False,
            keep_failed_instance=False
        )
        if self.args.instance:
            dt.reconfigure_for_existing_instance(
                self.args.instance, self.args.private_key_file
            )
        try:
            status = dt.process(shell_only=True, shell_on_errors=False)
        except do_tests.TestError as e:
            print("Error on ssh: %s" % e)
            return 1
        return status


class UploadCommand(GenericCommand):
    name = 'upload'
    help = 'Upload image'
    options = ['imagelabel', 'input', 'img-config',
               'upload-config', 'uploadlabel']

    def add_options(self):
        self.parser.add_argument(
            '--no-obsolete', action='store_true',
            help='Do not obsolete images with same name'
        )

    def _prepare(self):
        try:
            self.name = self.glance_data['name']
        except KeyError as e:
            raise NotFoundInConfigError(
                "Image name is not found in glance section"
                "in config files"
            )
        self.meta = self.glance_data.get('properties', {})
        self.container_format = self.glance_data.get(
            'container_format', 'bare'
        )
        self.disk_format = self.glance_data.get('disk_format', 'qcow2')
        self.public = self.glance_data.get('public', False)
        self.min_disk = self.glance_data.get('min_disk', 0)
        self.min_ram = self.glance_data.get('min_ram', 0)
        self.protected = self.glance_data.get('protected', False)

    def upload_to_glance(self):
        print("Uploading image")
        with image_preprocessing.Preprocess(
            input_filename=self.image['filename'],
            glance_data=self.glance_data,
            preprocessing_settings=self.upload_env.get('preprocessing', {})
        ) as upload_filename:
            self.image = self.os.upload_image(
                self.name,
                upload_filename,
                self.public,
                container_format=self.container_format,
                disk_format=self.disk_format,
                min_disk=self.min_disk,
                min_ram=self.min_ram,
                protected=self.protected,
                meta=self.meta
            )
            print(
                "Image ''%s' uploaded with uuid %s from file %s" % (
                    self.image.name, self.image.id, upload_filename
                )
            )

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
        return 0


class RotateCommand(GenericCommand):
    name = 'rotate'
    help = 'Remove unused obsolete images'
    options = ['upload-config', 'uploadlabel']

    def add_options(self):
        self.parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Do not delete anything, just print candidates"
        )

    def _command(self):
        candidate_list = self.os.find_obsolete_unused_candidates()
        if not candidate_list:
            print("No unused obsolete images found.")
            return 0
        if self.args.dry_run:
            print("Images are obsolete and unused, but wouldn't be removed per --dry-run:")
        else:
            print("Images are obsolete and unused and will be removed:")
        for candidate in candidate_list:
            print("%s" % (candidate,))
            if not self.args.dry_run:
                self.os.delete_image(candidate)
        return 0


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


class HelpCommand():
    #  special class to handle help messages
    def __init__(self, subparser):
        self.parser = subparser.add_parser('help', help='display help')
        self.parser.add_argument('name', nargs='?', help='Command to show help for')
        self.subparsers = subparser
        self.parser.set_defaults(command=self.command)

    def command(self, args):
        if args.name:
            self.subparsers.choices[args.name].print_help()
        else:
            print("Use help [name] to show help for given command")
            print("List of available commands:")
            print("\n".join(list(self.subparsers.choices.iterkeys())))


class Main(object):
    def __init__(self, command_line=None):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('--debug', help='Display this message', action='store_true', default=False)
        self.parser.add_argument('--version', help='Display version', action='version', version=version.VERSION_STRING)
        subparsers = self.parser.add_subparsers(title='commands')
        BuildCommand(subparsers)
        TestCommand(subparsers)
        ShellCommand(subparsers)
        UploadCommand(subparsers)
        RotateCommand(subparsers)
        ObsoleteCommand(subparsers)
        TransferCommand(subparsers)
        ValidateCommand(subparsers)
        HelpCommand(subparsers)
        self.args = self.parser.parse_args(command_line)

    def run(self):
        command = self.args.command
        return command(self.args)


def main(line=None):
    sad_table = {
        config.ConfigNotFound: 10,
        config.NotFoundInConfigError: 11,
        osclient.CredNotFound: 12,
        image_preprocessing.PreprocessError: 18,
        keystone_exceptions.http.Unauthorized: 20,
        glanceclient_exceptions.HTTPNotFound: 50,
        novaclient_exceptions.BadRequest: 60,
        novaclient_exceptions.Forbidden: 61,
        prepare_os.InstanceError: 70,
        do_tests.PortWaitError: 71
        # 80 is not handled here, but it is
    }
    m = Main(line)
    try:
        code = m.run()
    except tuple(sad_table.keys()) as e:
        code = sad_table[e.__class__]
        print("Error: %s, code %s" % (str(e), code))
    except (
        PrematureExitError,
        osclient.CredNotFound,
        osclient.OpenStackError,
        prepare_os.InstanceError,
        keystone_exceptions.ClientException,
        novaclient_exceptions.ClientException,
        osclient.DiscoveryError,
        glanceclient_exceptions.HTTPNotFound,
        IOError
    ) as e:
        print("Error: %s (%s)" % (str(e.message), e.__class__))
        code = 1
    except Exception as e:
        print("Bad exception: %s %s" % (e, e.__class__))
        raise
    return code


def init():
    if __name__ == "__main__":
        sys.exit(main())


init()
