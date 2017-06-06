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


def test_command_rotate_no_env(quick_commands):
    assert quick_commands.main([
        'rotate',
        'unknown_upload_env'
    ]) == 11


def test_command_rotate_bad_passwd(quick_commands):
    with VCR.use_cassette('test_command_rotate_bad_passwd.yaml'):
        assert quick_commands.main([
            'rotate',
            'upload_env_bad_credentials'
        ]) == 20


def test_command_rotate_nova_forbidden(quick_commands):
    with VCR.use_cassette('test_command_rotate_nova_forbidden.yaml'):
        assert quick_commands.main([
            'rotate',
            'upload_env_1'
        ]) == 61


def test_command_rotate_dry_run_with_candidates(quick_commands, capsys):
    with VCR.use_cassette('test_command_rotate_dry_run_with_candidates.yaml'):
        assert quick_commands.main([
            'rotate',
            'upload_env_2',
            '--dry-run'
        ]) == 0
        out = capsys.readouterr()[0]
        assert '8b52d0b9-a60f-48a5-aef3-d7e13272a506' in out  # first
        assert '33f0fd30-bd5d-428f-b220-ba42c47c5005' in out  # last


def test_command_rotate_with_candidates(quick_commands, capsys):
    # this test do real rotate and then run rotate once more
    # second run should yield empty list
    with VCR.use_cassette('test_command_rotate_with_candidates.yaml'):
        assert quick_commands.main([
            'rotate',
            'upload_env_2'
        ]) == 0
        out = capsys.readouterr()[0]
        assert 'will be removed' in out
        assert quick_commands.main([
            'rotate',
            'upload_env_2'
        ]) == 0
        out = capsys.readouterr()[0]
        assert 'No unused obsolete images found' in out


def test_command_rotate_no_candidates(quick_commands, capsys):
    # this test do real rotate and then run rotate once more
    # second run should yield empty list
    with VCR.use_cassette('test_command_rotate_no_candidates.yaml'):
        assert quick_commands.main([
            'rotate',
            'upload_env_2'
        ]) == 0
        out = capsys.readouterr()[0]
        assert 'No unused obsolete images found' in out


def test_command_rotate_dry_run_no_candidates(quick_commands, capsys):
    # this test do real rotate and then run rotate once more
    # second run should yield empty list
    with VCR.use_cassette('test_command_rotate_dry_run_no_candidates.yaml'):
        assert quick_commands.main([
            'rotate',
            'upload_env_2'
        ]) == 0
        out = capsys.readouterr()[0]
        assert 'No unused obsolete images found' in out
