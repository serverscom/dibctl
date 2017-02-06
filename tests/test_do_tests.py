#!/usr/bin/python
import mock
import pytest
import os
import inspect
import sys
from mock import sentinel


@pytest.fixture
def do_tests():
    from dibctl import do_tests
    return do_tests





def test_init_no_tests(do_tests):
    image = {}
    dt = do_tests.DoTests(image, sentinel.env)
    assert dt.tests_list == []
    assert dt.test_env == sentinel.env


def test_init_no_override(do_tests):
    image = {}
    dt = do_tests.DoTests(image, sentinel.env, image_uuid=sentinel.uuid)
    assert dt.tests_list == []
    assert dt.test_env == sentinel.env
    assert dt.delete_image is False
    assert dt.override_image_uuid == sentinel.uuid


def test_init_tests(do_tests):
    image = {
        'tests': {
            'tests_list': [sentinel.test]
        }
    }
    dt = do_tests.DoTests(image, sentinel.env)
    assert dt.tests_list == [sentinel.test]
    assert dt.test_env == sentinel.env


def test_chef_if_keep_stuff_after_fail_remove_all(do_tests):
    dt = do_tests.DoTests({}, sentinel.env)
    prep_os = mock.MagicMock()
    dt.keep_failed_instance = True
    dt.keep_failed_image = True
    dt.check_if_keep_stuff_after_fail(prep_os)
    assert prep_os.delete_instance is False
    assert prep_os.delete_keypair is False
    assert prep_os.delete_image is False


def test_run_test_bad_config(do_tests):
    dt = do_tests.DoTests({}, sentinel.env)
    with pytest.raises(do_tests.BadTestConfigError):
        dt.run_test({'one': 1, 'two': 2}, sentinel.config, sentinel.env)


def test_run_test_bad_runner(do_tests):
    dt = do_tests.DoTests({}, sentinel.env)
    with pytest.raises(do_tests.BadTestConfigError):
        dt.run_test({'badrunner': 1}, sentinel.config, sentinel.env)


def test_run_test_duplicate_runner(do_tests):
    dt = do_tests.DoTests({}, sentinel.env)
    with pytest.raises(do_tests.BadTestConfigError):
        dt.run_test({'pytest': 1, 'shell': 2}, sentinel.config, sentinel.env)



@pytest.mark.parametrize('continue_on_fail, result, expected', [
    [True, False, True],
    [True, True, True],
    [False, True, True],
    [False, False, False],
])
@pytest.mark.parametrize('runner', ['pytest', 'shell'])
def test_run_test_matrix(do_tests, runner, continue_on_fail, result, expected):
    dt = do_tests.DoTests({}, sentinel.env, continue_on_fail=continue_on_fail)
    with mock.patch.multiple(do_tests, pytest_runner=mock.DEFAULT, shell_runner=mock.DEFAULT) as mock_rs:
        mock_r = mock_rs[runner + '_runner']
        mock_r.runner.return_value = result
        assert dt.run_test({runner: sentinel.path}, sentinel.config, sentinel.var) is expected
        assert mock_r.runner.called


@pytest.mark.parametrize('port', [False, 22])
def test_run_all_tests_minimal(do_tests, port, capsys):
    env = {
        'nova': {
            'flavor': 'some flavor'
        }
    }
    image = {
        'tests': {
            'wait_for_port': port,
            'tests_list': []
        }
    }
    dt = do_tests.DoTests(image, env)
    with mock.patch.object(do_tests.prepare_os, "PrepOS"):
        assert dt.run_all_tests() is True
    assert 'Done' in capsys.readouterr()[0]


def test_run_all_tests_port_timeout(do_tests):
    env = {
        'nova': {
            'flavor': 'some flavor'
        }
    }
    image = {
        'tests': {
            'wait_for_port': 22,
            'tests_list': []
        }
    }
    dt = do_tests.DoTests(image, env)
    with mock.patch.object(do_tests.prepare_os, "PrepOS") as mock_prep_os_class:
        mock_prep_os = mock.MagicMock()
        mock_prep_os.wait_for_port.return_value = False
        mock_enter = mock.MagicMock()
        mock_enter.__enter__.return_value = mock_prep_os
        mock_prep_os_class.return_value = mock_enter
        with pytest.raises(do_tests.TestError):
            dt.run_all_tests()


def test_run_all_tests_with_tests(do_tests, capsys):
    env = {
        'nova': {
            'flavor': 'some flavor'
        }
    }
    image = {
        'tests': {
            'wait_for_port': 22,
            'tests_list': [{'pytest': sentinel.path1}, {'shell': sentinel.path2}]
        }
    }
    dt = do_tests.DoTests(image, env)
    with mock.patch.multiple(do_tests, pytest_runner=mock.DEFAULT, shell_runner=mock.DEFAULT):
        with mock.patch.object(do_tests.prepare_os, "PrepOS") as mock_prep_os_class:
            mock_prep_os = mock.MagicMock()
            mock_enter = mock.MagicMock()
            mock_enter.__enter__.return_value = mock_prep_os
            mock_prep_os_class.return_value = mock_enter
            assert dt.run_all_tests() is True


def test_run_all_tests_fail(do_tests, capsys):
    env = {
        'nova': {
            'flavor': 'some flavor'
        }
    }
    image = {
        'tests': {
            'wait_for_port': 22,
            'tests_list': [{'pytest': sentinel.path1}, {'pytest': sentinel.path2}]
        }
    }
    dt = do_tests.DoTests(image, env)
    with mock.patch.object(do_tests.pytest_runner, "runner") as runner:
        runner.side_effect = [False, ValueError("Shouldn't be called")]
        with mock.patch.object(do_tests.prepare_os, "PrepOS") as mock_prep_os_class:
            mock_prep_os = mock.MagicMock()
            mock_enter = mock.MagicMock()
            mock_enter.__enter__.return_value = mock_prep_os
            mock_prep_os_class.return_value = mock_enter
            assert dt.run_all_tests() is False
            assert runner.call_count == 1


if __name__ == "__main__":
    ourfilename = os.path.abspath(inspect.getfile(inspect.currentframe()))
    currentdir = os.path.dirname(ourfilename)
    parentdir = os.path.dirname(currentdir)
    file_to_test = os.path.join(
        parentdir,
        os.path.basename(parentdir),
        os.path.basename(ourfilename).replace("test_", '', 1)
    )
    pytest.main([
     "-vv",
     "--cov", file_to_test,
     "--cov-report", "term-missing"
     ] + sys.argv)
