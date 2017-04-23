import pytest
import mock
import vcr


@pytest.fixture
def quick_commands(MockSocket):
    from dibctl import commands
    with mock.patch.object(commands.prepare_os.time, "sleep"):
        with mock.patch.object(commands.prepare_os, "socket", MockSocket([0])):
            yield commands


def test_no_configs(quick_commands, MockSocket):
    assert quick_commands.main([
            'test',
            'xenial',
            '--images-config', 'not_existing_name'
        ]) == 10


def test_not_found_in_config(quick_commands, MockSocket):
    assert quick_commands.main([
            'test',
            'no_such_image_in_config'
        ]) == 11


def test_existing_image_success(quick_commands, MockSocket):
    with vcr.use_cassette('cassettes/test_existing_image_success.yaml'):
        assert quick_commands.main([
                'test',
                'xenial',
                '--use-existing-image',
                '2eb14fc3-4edc-4068-8748-988f369302c2'
            ]) == 0


def test_non_existing_image_exit_code_50(quick_commands):
    with vcr.use_cassette('cassettes/test_non_existing_image.yaml'):
        assert quick_commands.main([
                'test',
                'xenial',
                '--use-existing-image',
                'deadbeaf-0000-0000-0000-b7a14cdd1169'
            ]) == 50
