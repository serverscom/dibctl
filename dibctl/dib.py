'''Wrapper around diskimage builder'''
import subprocess
import os
import sys
import pprint


class NoElementsError(IndexError):
    pass


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
        print("Comand line: %s" % " ".join(self.cmdline))

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
