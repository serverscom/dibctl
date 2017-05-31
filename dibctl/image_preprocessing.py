import config
import subprocess
import sys
import os


class PreprocessError(Exception):
    pass


class Preprocess(object):
    def __init__(self, input_filename, glance_data, preprocessing_settings):
        self.input_filename = input_filename
        self.glance_data = glance_data
        self.preprocessing_settings = preprocessing_settings
        self.delete_after = self.preprocessing_settings.get('delete_processed_after_upload', True)
        self.use_existing = self.preprocessing_settings.get('use_existing', False)

    def prep_output_name(self, allowed_vars):
        try:
            return self.preprocessing_settings["output_filename"] % allowed_vars
        except (KeyError, ValueError) as e:
            raise config.InvaidConfigError(
                'Invalid string interpolation in output filename: %s: %s' % (
                    self.preprocessing_settings["output_filename"],
                    e.message
                )
            )

    def prep_cmdline(self, allowed_vars):
        try:
            return self.preprocessing_settings['cmdline'] % allowed_vars
        except (KeyError, ValueError) as e:
            raise config.InvaidConfigError(
                'Invalid string interpolation in cmdline: %s: %s' % (
                        self.preprocessing_settings["cmdline"],
                        e.message
                    )
                )

    def interpolate(self):
        allowed_vars = {
            'input_filename': self.input_filename,
            'disk_format': self.glance_data.get('disk_format', 'qcow2'),
            'container_format': self.glance_data.get('container_format', 'bare')
        }

        self.output_filename = self.prep_output_name(allowed_vars)
        allowed_vars['output_filename'] = self.output_filename
        self.command_line = self.prep_cmdline(allowed_vars)

    def __enter__(self):
        if not self.preprocessing_settings:
            return self.input_filename

        self.interpolate()
        self.run()
        return self.output_filename

    def __exit__(self, exc_type, exc_value, traceback):
        if self.preprocessing_settings:
            if self.delete_after and not self.use_existing:
                os.remove(self.output_filename)

    def run(self):
        if os.path.isfile(self.output_filename):
            if self.use_existing:
                return self.output_filename
            else:
                os.remove(self.output_filename)
        sys.stdout.flush()
        try:
            subprocess.check_call(self.command_line, shell=True, stdout=sys.stdout, stderr=sys.stderr, stdin=None)
        except subprocess.CalledProcessError as e:
            raise PreprocessError('Preprocessing failed with code %s' % e.returncode)
        if not os.path.isfile(self.output_filename):
            raise PreprocessError('There is no output file %s after preprocess had finished')
        sys.stdout.flush()
