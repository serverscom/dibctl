import vcr
import os
import mock


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
        match_on=['uri', 'method']
    )


def teardown_modlue(module):
    global curdir
    os.chdir(curdir)


def test_no_image_config_code_10(quick_commands):
    assert quick_commands.main([
            'test',
            'xenial',
            '--images-config', 'not_existing_name'
        ]) == 10


def test_no_test_config_code_10(quick_commands):
    assert quick_commands.main([
            'test',
            'xenial',
            '--test-config', 'not_existing_name'
        ]) == 10


def test_no_upload_config_code_10(quick_commands):
    assert quick_commands.main([
            'upload',
            'xenial',
            'nowhere',
            '--upload-config', 'not_existing_name'
        ]) == 10


def test_not_found_in_config_code_11(quick_commands):
    assert quick_commands.main([
            'test',
            'no_such_image_in_config'
        ]) == 11


def test_existing_image_success_code_0(quick_commands):
    with VCR.use_cassette('test_existing_image_success.yaml'):
        assert quick_commands.main([
                'test',
                'xenial',
                '--use-existing-image',
                '2eb14fc3-4edc-4068-8748-988f369302c2'
            ]) == 0


def test_existing_image_fail_code_80(quick_commands):
    with VCR.use_cassette('test_existing_image_fail.yaml'):
        assert quick_commands.main([
                'test',
                'xenial_fail',
                '--use-existing-image',
                '2eb14fc3-4edc-4068-8748-988f369302c2'
            ]) == 80  # this code is inside __command for TestCommand


def test_non_existing_image_code_50(quick_commands):
    with VCR.use_cassette('test_non_existing_image.yaml'):
        assert quick_commands.main([
                'test',
                'xenial',
                '--use-existing-image',
                'deadbeaf-0000-0000-0000-b7a14cdd1169'
            ]) == 50


def test_non_existing_network_code_60(quick_commands):
    with VCR.use_cassette('test_non_existing_network.yaml'):
        assert quick_commands.main([
                'test',
                'xenial',
                '--use-existing-image',
                '2eb14fc3-4edc-4068-8748-988f369302c2',
                '--environment',
                'bad_network_id'
            ]) == 60


def test_instance_is_not_answer_port(quick_commands):
    with VCR.use_cassette('instance_is_not_answer_port.yaml'):
        quick_commands.prepare_os.socket.sequence = [None]
        assert quick_commands.main([
                'test',
                'xenial',
                '--use-existing-image',
                '2eb14fc3-4edc-4068-8748-988f369302c2',
            ]) == 71


def test_instance_is_not_answer_port_with_upload(quick_commands):
    with VCR.use_cassette('instance_is_not_answer_port_with_upload.yaml'):
        quick_commands.prepare_os.socket.sequence = [None]
        assert quick_commands.main([
                'test',
                'xenial',
                '--input',
                'empty.img.qcow2',
            ]) == 71


def test_instance_in_error(quick_commands):
    def full_read(ignore_self, filename):
        return open(filename, 'rb', buffering=65536).read()
    with mock.patch.object(quick_commands.do_tests.prepare_os.osclient.OSClient, '_file_to_upload', full_read):
        with VCR.use_cassette('instance_in_error.yaml'):
            assert quick_commands.main([
                    'test',
                    'xenial',
                    '--input',
                    'damaged.img.qcow2'
                ]) == 70


def test_normal_upload(quick_commands):
    def full_read(ignore_self, filename):
        return open(filename, 'rb', buffering=65536).read()
    with mock.patch.object(quick_commands.do_tests.prepare_os.osclient.OSClient, '_file_to_upload', full_read):
        with VCR.use_cassette('normal_upload.yaml'):
            assert quick_commands.main([
                    'test',
                    'xenial'
                ]) == 0
