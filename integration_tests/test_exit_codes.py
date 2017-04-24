import vcr
import os


def setup_module(module):
    global curdir
    curdir = os.getcwd()
    if 'integration_tests' not in curdir:
        os.chdir('integration_tests')


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
    with vcr.use_cassette('cassettes/test_existing_image_success.yaml'):
        assert quick_commands.main([
                'test',
                'xenial',
                '--use-existing-image',
                '2eb14fc3-4edc-4068-8748-988f369302c2'
            ]) == 0


def test_existing_image_fail_code(quick_commands):
    with vcr.use_cassette('cassettes/test_existing_image_fail.yaml'):
        assert quick_commands.main([
                'test',
                'xenial_fail',
                '--use-existing-image',
                '2eb14fc3-4edc-4068-8748-988f369302c2'
            ]) == 0


def test_non_existing_image_code_50(quick_commands):
    with vcr.use_cassette('cassettes/test_non_existing_image.yaml'):
        assert quick_commands.main([
                'test',
                'xenial',
                '--use-existing-image',
                'deadbeaf-0000-0000-0000-b7a14cdd1169'
            ]) == 50


def test_non_existing_network_code_60(quick_commands):
    with vcr.use_cassette('cassettes/test_non_existing_network.yaml'):
        assert quick_commands.main([
                'test',
                'xenial',
                '--use-existing-image',
                '2eb14fc3-4edc-4068-8748-988f369302c2',
                '--environment',
                'bad_network_id'
            ]) == 60


def test_instance_is_not_answer_port(quick_commands):
    with vcr.use_cassette('cassettes/instance_is_not_answer_port.yaml'):
        quick_commands.prepare_os.socket.sequence = [None]
        assert quick_commands.main([
                'test',
                'xenial',
                '--use-existing-image',
                '2eb14fc3-4edc-4068-8748-988f369302c2',
            ]) == 71
