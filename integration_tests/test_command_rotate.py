import os
import pytest


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
# to rewrite cassette one need to run (update) upload tests
# test order is important.

def test_command_rotate_dry_run_with_candidates(
    quick_commands,
    capsys,
    happy_vcr
):
    '''
        This test checks if:
        - rotate can see images
        - dry run is respected (we ran this test twice)

        This test is hard to update as it depends on
        precise uuid values in the output. If cassette was
        overwritten, one need to update values in assert.

        This test need to have no used images (with booted instances)
    '''
    with happy_vcr('test_command_rotate_dry_run_with_candidates.yaml'):
        for interation in (1, 2):
            assert quick_commands.main([
                'rotate',
                'upload_env_1',
                '--dry-run'
            ]) == 0
            out = capsys.readouterr()[0]
            assert '7b055f53-3221-43b3-a047-9ad7ddebbb5f' in out  # first
            assert '45d69b26-6c4b-48de-adc5-0a83183e01dd' in out  # last


def test_command_rotate_with_candidates(quick_commands, capsys, happy_vcr):
    '''
        This test check actually remove unused obsolete images
        This test need to have no used images (with booted instances)

        Cassette update to this test is destructive, and to repeat it
        one need to update upload tests.
    '''
    with happy_vcr('test_command_rotate_with_candidates.yaml'):
        assert quick_commands.main([
            'rotate',
            'upload_env_1'
        ]) == 0
        out = capsys.readouterr()[0]
        assert 'will be removed' in out
        assert '7b055f53-3221-43b3-a047-9ad7ddebbb5f' in out  # first
        assert '45d69b26-6c4b-48de-adc5-0a83183e01dd' in out  # last


def test_command_rotate_no_candidates(quick_commands, capsys, happy_vcr):
    '''
        This test checks if we have no images to remove
        it expected to be updated after test_command_rotate_with_candidates
    '''
    with happy_vcr('test_command_rotate_no_candidates.yaml'):
        assert quick_commands.main([
            'rotate',
            'upload_env_1'
        ]) == 0
        out = capsys.readouterr()[0]
        assert 'No unused obsolete images found' in out


def test_command_rotate_dry_run_no_candidates(
    quick_commands,
    capsys,
    happy_vcr
):
    '''
        This test checks if we can works fine if there are no images to remove
        (no unused images).

        To update this test one should update test_command_rotate_no_candidates
        first.
    '''
    with happy_vcr('test_command_rotate_dry_run_no_candidates.yaml'):
        assert quick_commands.main([
            'rotate',
            'upload_env_1'
        ]) == 0
        out = capsys.readouterr()[0]
        assert 'No unused obsolete images found' in out


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
