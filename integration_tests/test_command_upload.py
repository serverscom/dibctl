
import os
import mock


def setup_module(module):
    global saved_curdir
    global log
    saved_curdir = os.getcwd()
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
    if 'integration_tests' not in saved_curdir:
        os.chdir('integration_tests')


def teardown_modlue(module):
    global saved_curdir
    os.chdir(saved_curdir)


# HAPPY TESTS (normal workflow)

def test_upload_image_normal_no_obsolete(quick_commands, happy_vcr):
    '''
        Thise test check if we can upload image.
        It assumes that we have no other copies of image to obsolete
    '''
    def full_read(ignore_self, filename):
        return open(filename, 'rb', buffering=65536).read()
    with mock.patch.object(
        quick_commands.do_tests.prepare_os.osclient.OSClient,
        '_file_to_upload',
        full_read
    ):
        with happy_vcr('test_upload_image_normal_no_obsolete.yaml'):
            assert quick_commands.main([
                    'upload',
                    'overrided_raw_format',
                    'upload_env_1'
                ]) == 0


def test_upload_image_normal_obsolete(quick_commands, happy_vcr):
    '''
        Thise test check if we can upload image and obsolete older copy.
        It assumes that we have older copy of the image
    '''
    def full_read(ignore_self, filename):
        return open(filename, 'rb', buffering=65536).read()
    with mock.patch.object(
        quick_commands.do_tests.prepare_os.osclient.OSClient,
        '_file_to_upload',
        full_read
    ):
        with happy_vcr('test_upload_image_normal_obsolete.yaml'):
            assert quick_commands.main([
                    'upload',
                    'overrided_raw_format',
                    'upload_env_1'
                ]) == 0


def test_upload_image_normal_no_obsolete_convertion(quick_commands, happy_vcr):
    '''
        Thise test check if we can convert image before upload and then
        upload it.
        It assumes that we have older copy of the image to obsolete.
        (obsoletion is not the part of the test but it makes easier to
        rerecord test)
    '''
    def full_read(ignore_self, filename):
        return open(filename, 'rb', buffering=65536).read()
    with mock.patch.object(
        quick_commands.do_tests.prepare_os.osclient.OSClient,
        '_file_to_upload',
        full_read
    ):
        with happy_vcr('test_upload_image_normal_no_obsolete_convertion.yaml'):
            assert quick_commands.main([
                    'upload',
                    'overrided_raw_format',
                    'upload_env_raw'
                ]) == 0


# SAD TESTS (handling errors)

def test_upload_image_bad_credentials(quick_commands, happy_vcr):
    '''
        This test should fail due to bad credentials
        it's a bit akward as we conseal 'bad credentials' from cassette,
        but nevertheless it's still valid
    '''
    def full_read(ignore_self, filename):
        return open(filename, 'rb', buffering=65536).read()
    with mock.patch.object(
        quick_commands.do_tests.prepare_os.osclient.OSClient,
        '_file_to_upload',
        full_read
    ):
        with happy_vcr('test_upload_bad_credentials.yaml'):
            assert quick_commands.main([
                    'upload',
                    'overrided_raw_format',
                    'upload_env_bad_credentials'
                ]) == 20


def test_upload_image_error_for_convertion(quick_commands):
    '''
        This test should fail on convertion, no actual upload
        should happen
    '''
    assert quick_commands.main([
        'upload',
        'xenial',
        'env_with_failed_convertion'
    ]) == 18
