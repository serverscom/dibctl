'''Wrapper around diskimage builder'''
import subprocess
import os
import sys
import pprint
import pkg_resources
import semantic_version


class NoElementsError(IndexError):
    pass


class BadDibVersion(EnvironmentError):
    pass


class BadVersion(ValueError):
    pass


class NoDibError(BadDibVersion):
    pass


def _version(text):
    try:
        return semantic_version.Version.coerce(text)
    except StandardError as e:
        raise BadVersion("''%s' is not a proper version: %s" % (text, e.message))


def validate_version(min_version, max_version):
    dib_version = get_installed_version()
    if min_version:
        if dib_version < _version(min_version):
            raise BadDibVersion(
                'dib.min_version (%s) for image is greater that installed (%s)' % (
                    min_version,
                    dib_version
                )
            )
    if max_version:
        if dib_version > _version(max_version):
            raise BadDibVersion(
                'dib.max_version (%s) for image is less than installed (%s)' % (
                    max_version,
                    dib_version
                )
            )
    return True


def get_installed_version():
    try:
        version = pkg_resources.get_distribution('diskimage_builder').version
    except pkg_resources.DistributionNotFound:
        raise NoDibError("diskimage-builder is not available (as python package)")
    return semantic_version.Version.coerce(version)


class DIB():
    def __init__(
        self,
        filename,
        elements,
        arch="amd64",
        exec_path=None,
        offline=False,
        tracing=False,
        additional_options=[],
        env={}
    ):
        if not elements:
            raise NoElementsError("No elements to build")
        self.elements = elements
        self.filename = filename
        self.exec_path = exec_path or 'disk-image-create'
        self.arch = arch
        self.tracing = tracing
        self.offline = offline
        self.additional_options = additional_options
        self.env = env
        self.cmdline = []
        self._create_cmdline()

    def _create_cmdline(self):
        self.cmdline = [self.exec_path]
        self.cmdline.extend(['-a', self.arch])
        if self.tracing:
            self.cmdline.append('-x')
        if self.offline:
            self.cmdline.append('--offline')
        self.cmdline.extend(["-o", self.filename])
        if self.additional_options:
            self.cmdline.extend(self.additional_options)
        self.cmdline.extend(self.elements)

    def _prep_env(self):
        new_env = dict(os.environ)
        new_env.update({'ARCH': self.arch})
        new_env.update(self.env)
        return new_env

    def print_settings(self, env):
        print("Will run disk-image-create:")
        print("Environment:")
        pprint.pprint(env)
        print("Command line: %s" % " ".join(self.cmdline))

    def run(self):
        env = self._prep_env()
        self.print_settings(env)
        sys.stdout.flush()
        dib_process = subprocess.Popen(
            self.cmdline,
            stdout=sys.stdout,
            stdin=None,
            stderr=sys.stderr,
            env=env,
            bufsize=1
        )
        self.returncode = dib_process.wait()
        return self.returncode
