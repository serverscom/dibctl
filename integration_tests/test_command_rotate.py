import os


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


# SAD tests

def test_command_rotate_no_env(quick_commands):
    ''' This test check how dibctl fails if env is not found in config '''
    assert quick_commands.main([
        'rotate',
        'unknown_upload_env'
    ]) == 11


def test_command_rotate_bad_passwd(quick_commands, happy_vcr):
    '''
        This test check fail code for bad password situation
    '''
    with happy_vcr('test_command_rotate_bad_passwd.yaml'):
        assert quick_commands.main([
            'rotate',
            'upload_env_bad_credentials'
        ]) == 20


def test_command_rotate_nova_forbidden(quick_commands, happy_vcr):
    '''
        This test check if forbidden message from nova is handled
        correctly.
        If user has no permissions to view instances of other users,
        than nova return message:
        Policy doesn't allow os_compute_api:servers:detail:get_all_tenants
        to be performed

        To update cassette one need to change
        os_compute_api:servers:detail:get_all_tenants in policy.json or
        use account withous special privelege.
    '''
    with happy_vcr('test_command_rotate_nova_forbidden.yaml'):
        assert quick_commands.main([
            'rotate',
            'upload_env_1_no_enough_priveleges'
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
