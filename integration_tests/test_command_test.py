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


# HAPPY tests

def test_test_normal(quick_commands, happy_vcr, capfd):
    '''
        This test check if we can do test
        workflow:
            - Upload new image
            - Create new keypair
            - Start new instance
            - cleanup

            Please not: it does not upload real image (it's too slow to do),
            Mocked functions:
            - check if port is alive
            - test successfull anyway (simple_success.bash)

            To update this test:
            - check if network uuids are vaild (in config)
            - it need normal user priveleges
    '''
    def full_read(ignore_self, filename):
        return open(filename, 'rb', buffering=65536).read()
    with mock.patch.object(
        quick_commands.do_tests.prepare_os.osclient.OSClient,
        '_file_to_upload',
        full_read
    ):
        with happy_vcr('test_test_normal.yaml'):
            assert quick_commands.main([
                    'test',
                    'xenial'
                ]) == 0
            out = capfd.readouterr()[0]
            assert 'All tests passed successfully' in out
            assert 'Removing instance' in out
            assert 'Removing ssh key' in out
            assert 'Removing image' in out
            assert 'Clearing done' in out


def test_test_existing_image_success(quick_commands, happy_vcr, capfd):
    '''
        This test check if we can do test
        workflow:
            - Create new keypair
            - Start new instance
            - cleanup

            Please not: it does not upload real image (it's too slow to do),
            Mocked functions:
            - check if port is alive
            - test successfull anyway (simple_success.bash)

            To update this test:
            - check if network uuids are vaild (in config)
            - check if image uuid is valid (it should be uploaded)
            - it need normal user priveleges
    '''
    with happy_vcr('test_test_existing_image_success.yaml'):
        assert quick_commands.main([
                'test',
                'xenial',
                '--use-existing-image',
                'f4ffd69e-20c9-40e6-b22a-808f00bf6458'
            ]) == 0
        out = capfd.readouterr()[0]
        assert 'All tests passed successfully' in out
        assert 'Removing instance' in out
        assert 'Removing ssh key' in out
        assert 'Not removing image' in out
        assert 'Removing image' not in out
        assert 'Clearing done' in out


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
