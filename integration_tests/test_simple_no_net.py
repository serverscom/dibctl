import os


# this file contains test which did not require vcr or http

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
