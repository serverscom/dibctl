
import os
import mock


def setup_module(module):
    global curdir
    global log
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


def test_upload_error_for_convertion(quick_commands):
    assert quick_commands.main([
        'upload',
        'xenial',
        'env_with_failed_convertion'
    ]) == 18

def test_normal_upload(quick_commands):
    def full_read(ignore_self, filename):
        return open(filename, 'rb', buffering=65536).read()
    with mock.patch.object(quick_commands.do_tests.prepare_os.osclient.OSClient, '_file_to_upload', full_read):
        with VCR.use_cassette('normal_upload.yaml'):
            assert quick_commands.main([
                    'test',
                    'xenial'
                ]) == 0


def test_remove_this_new_auth_clearance(quick_commands, happy_vcr):
    with happy_vcr.VCR.use_cassette('killme.yaml', before_record_request=happy_vcr.filter_request, before_record_response=happy_vcr.filter_response):
        assert quick_commands.main([
            'upload',
            '--images-config',
            '../temp/images.yaml',
            '--upload-config',
            '../temp/upload.yaml',
            '--input',
            '../temp/blob.img',
            'blob',
            'nova-lab-1'
        ]) == 0
