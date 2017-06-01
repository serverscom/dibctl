import vcr
import os
import mock
import logging
import sys


def setup_module(module):
    global curdir
    curdir = os.getcwd()
    for forbidden in [
        'OS_AUTH_URL',
        'OS_USERNAME',
        'OS_PASSWORD',
        'OS_TENANT_NAME',
        'OS_PROJECT_NAME',
        'OS_PROJECT'
    ]:
        if forbidden in os.environ:
            del os.environ[forbidden]
    if 'integration_tests' not in curdir:
        os.chdir('integration_tests')

    global VCR
    VCR = vcr.VCR(
        cassette_library_dir='cassettes/',
        record_mode='once',
        match_on=['uri', 'method', 'headers', 'body']
    )
    VCR.filter_headers = ('Content-Length', 'Accept-Encoding', 'User-Agent', 'date', 'x-distribution')
    logging.basicConfig()
    vcr_log = logging.getLogger('vcr')
    vcr_log.setLevel(logging.DEBUG)
    ch = logging.FileHandler('/tmp/requests.log', mode='w')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    ch.setLevel(logging.INFO)
    vcr_log.addHandler(ch)
    vcr_log.info('Set up logging')
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)


def teardown_modlue(module):
    global curdir
    os.chdir(curdir)


def test_upload_empty_image_normal_no_obsolete(quick_commands):
    def full_read(ignore_self, filename):
        return open(filename, 'rb', buffering=65536).read()
    with mock.patch.object(quick_commands.do_tests.prepare_os.osclient.OSClient, '_file_to_upload', full_read):
        with VCR.use_cassette('test_upload_empty_image_normal_no_obsolete.yaml'):
            assert quick_commands.main([
                    'upload',
                    'overrided_raw_format',
                    'upload_env_1'
                ]) == 0


def test_upload_empty_image_normal_no_obsolete_format_raw_temporaly(quick_commands):
    def full_read(ignore_self, filename):
        return open(filename, 'rb', buffering=65536).read()
    with mock.patch.object(quick_commands.do_tests.prepare_os.osclient.OSClient, '_file_to_upload', full_read):
        with VCR.use_cassette('test_upload_empty_image_normal_no_obsolete_format_raw_temporaly.yaml'):
            assert quick_commands.main([
                    'upload',
                    'overrided_raw_format',
                    'upload_env_raw'
                ]) == 0


def test_upload_empty_image_normal_obsolete(quick_commands):
    def full_read(ignore_self, filename):
        return open(filename, 'rb', buffering=65536).read()
    with mock.patch.object(quick_commands.do_tests.prepare_os.osclient.OSClient, '_file_to_upload', full_read):
        with VCR.use_cassette('test_upload_empty_image_normal_obsolete.yaml'):
            assert quick_commands.main([
                    'upload',
                    'overrided_raw_format',
                    'upload_env_1'
                ]) == 0


def test_upload_bad_credentials(quick_commands):
    def full_read(ignore_self, filename):
        return open(filename, 'rb', buffering=65536).read()
    with mock.patch.object(quick_commands.do_tests.prepare_os.osclient.OSClient, '_file_to_upload', full_read):
        with VCR.use_cassette('test_upload_bad_credentials.yaml'):
            assert quick_commands.main([
                    'upload',
                    'overrided_raw_format',
                    'upload_env_bad_credentials'
                ]) == 20
