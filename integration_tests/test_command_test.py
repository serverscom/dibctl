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


# SAD tests

def test_test_imagetest_failed_code_80(quick_commands, happy_vcr, capfd):
    '''
        This test checks how dibctl handle 'test failed'
        situation when image test failed.
        It expected to start instance successfully.
        It uses exsisting image

        This test uses mocked port ready and image test which always fails.

        To update this test:
        - check if network uuids are vaild (in config)
        - check if image uuid is valid (it should be uploaded)
        - it need normal user priveleges
    '''
    with happy_vcr('test_test_imagetest_failed_code_80.yaml'):
        assert quick_commands.main([
                'test',
                'xenial_fail',
                '--use-existing-image',
                '2eb14fc3-4edc-4068-8748-988f369302c2'
            ]) == 80  # this code is inside __command() in TestCommand
        out = capfd.readouterr()[0]
        assert 'Some tests failed' in out
        assert 'Removing instance' in out
        assert 'Removing ssh key' in out
        assert 'Not removing image' in out
        assert 'Removing image' not in out
        assert 'Clearing done' in out


def test_non_existing_image_code_50(quick_commands, happy_vcr):
    '''
        This test checks how dibctl handle when there is no image
        inside openstack and --use-existing-image option is used.

        To update this test:
        - check if network uuids are vaild (in config)
        - check if image with given uuid does not exist
        - it need normal user priveleges
    '''
    with happy_vcr('test_non_existing_image_code_50.yaml'):
        assert quick_commands.main([
                'test',
                'xenial',
                '--use-existing-image',
                'deadbeaf-0000-0000-0000-b7a14cdd1169'
            ]) == 50


def test_non_existing_network_code_60(quick_commands, happy_vcr, capfd):
    '''
        This test checks how dibctl handle when there is no network
        found.

        To update this test:
        - check if network uuids are invaild (in config)
        - it need normal user priveleges
    '''
    with happy_vcr('test_non_existing_network_code_60.yaml'):
        assert quick_commands.main([
                'test',
                'xenial',
                '--environment',
                'bad_network_id'
            ]) == 60
        out = capfd.readouterr()[0]
        assert 'Removing image' in out
        assert 'Removing ssh key' in out


def test_instance_is_not_answer_port_code_71(quick_commands, happy_vcr, capfd):
    '''
        This test checks how dibctl handle when instance does not
        reply to port in timely manner.

        It uses mocked 'non answering port'

        To update this test:
        - check if network uuids are vaild (in config)
        - it need normal user priveleges
    '''
    def full_read(ignore_self, filename):
        return open(filename, 'rb', buffering=65536).read()
    with happy_vcr('test_instance_is_not_answer_port_code_71.yaml'):
        quick_commands.prepare_os.socket.sequence = [None]
        with mock.patch.object(
            quick_commands.do_tests.prepare_os.osclient.OSClient,
            '_file_to_upload',
            full_read
        ):
            assert quick_commands.main([
                    'test',
                    'xenial'
                ]) == 71
            out = capfd.readouterr()[0]
            assert 'Instance is not accepting connection' in out
            assert 'Removing instance' in out
            assert 'Removing ssh key' in out
            assert 'Removing image' in out


def test_instance_in_error_state_code_70(quick_commands, happy_vcr, capfd):
    '''
        This test check how handled instance in ERROR state.
        To make instance 'ERROR' we use low-level trick with invalid
        image format (damaged.img.qcow2), which cause errors on libvirt+qemu.

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
        with happy_vcr('test_instance_in_error_state_code_70.yaml'):
            assert quick_commands.main([
                    'test',
                    'xenial',
                    '--input',
                    'damaged.img.qcow2'
                ]) == 70
            out = capfd.readouterr()[0]
            assert "is 'ERROR' (expected 'ACTIVE')" in out
            assert 'Removing instance' in out
            assert 'Removing ssh key' in out
            assert 'Removing image' in out
