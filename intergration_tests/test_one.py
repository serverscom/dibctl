import pytest
import mock
import vcr


@pytest.fixture
def quick_commands(MockSocket):
    from dibctl import commands
    with mock.patch.object(commands.prepare_os.time, "sleep"):
        with mock.patch.object(commands.prepare_os, "socket", MockSocket([0])):
            yield commands


def setup_module(module):
    print "hello"


def test_foo(quick_commands, MockSocket):
    with vcr.use_cassette('cassettes/test_foo.yaml'):
        m = quick_commands.Main([
                'test',
                'xenial',
                '--use-existing-image',
                '2eb14fc3-4edc-4068-8748-988f369302c2'
            ])
        assert m.run() == 0


def test_non_existing_image(quick_commands, MockSocket):
    with vcr.use_cassette('cassettes/test_non_existing_image.yaml'):
        m = quick_commands.Main([
                'test',
                'xenial',
                '--use-existing-image',
                'deadbeaf-0000-0000-0000-b7a14cdd1169'
            ])
        assert m.run() == 0
