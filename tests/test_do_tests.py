#!/usr/bin/python
import mock
import pytest
import os
import inspect
import sys
from mock import sentinel


@pytest.fixture
def Config():
    from dibctl import config
    return config.Config


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


def test_init_tests(do_tests, Config):
    image = Config({
        'tests': {
            'tests_list': ['test']
        }
    })
    env = Config({})
    dt = do_tests.DoTests(image, env)
    assert dt.tests_list == ['test']


def test_run_test_bad_config(do_tests):
    dt = do_tests.DoTests({}, sentinel.env)
    with pytest.raises(do_tests.BadTestConfigError):
        dt.run_test(sentinel.ssh, {'one': 1, 'two': 2}, sentinel.config, sentinel.env)


def test_run_test_bad_runner(do_tests):
    dt = do_tests.DoTests({}, sentinel.env)
    with pytest.raises(do_tests.BadTestConfigError):
        dt.run_test(sentinel.ssh, {'badrunner': 1}, sentinel.config, sentinel.env)


def test_run_test_duplicate_runner(do_tests):
    dt = do_tests.DoTests({}, sentinel.env)
    with pytest.raises(do_tests.BadTestConfigError):
        dt.run_test(sentinel.ssh, {'pytest': 1, 'shell': 2}, sentinel.config, sentinel.env)


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
        assert dt.run_test(sentinel.ssh, {runner: sentinel.path}, sentinel.config, sentinel.var) is expected
        assert mock_r.runner.called


def test_init_ssh_with_data(do_tests):
    env = {
        'nova': {
            'flavor': 'some flavor'
        }
    }
    image = {
        'tests': {
            'tests_list': [],
            'ssh': {
                'username': 'user'
            }
        }
    }
    dt = do_tests.DoTests(image, env)
    dt.init_ssh(mock.MagicMock())
    assert dt.ssh is not None


def test_wait_port_good(do_tests, Config):
    env = {
        'nova': {
            'flavor': 'some flavor'
        }
    }
    image = {
        'tests': {
            'tests_list': [],
            'wait_for_port': 22,
            'port_wait_timeout': 180
        }
    }
    dt = do_tests.DoTests(Config(image), Config(env))
    mock_prep_os = mock.MagicMock()
    assert dt.wait_port(mock_prep_os) is True
    assert mock_prep_os.wait_for_port.call_args == mock.call(22, 180)


@pytest.mark.parametrize('env_timeout, image_timeout, result', [
    [1, 2, 2],
    [2, 1, 2],
])
def test_get_port_timeout_uses_max(do_tests, Config, env_timeout, image_timeout, result):
    env = {
        'nova': {
            'flavor': 'some flavor'
        },
        'tests': {
            'port_wait_timeout': env_timeout
        }
    }
    image = {
        'tests': {
            'tests_list': [],
            'wait_for_port': 22,
            'port_wait_timeout': image_timeout
        }
    }
    dt = do_tests.DoTests(Config(image), Config(env))
    mock_prep_os = mock.MagicMock()
    dt.wait_port(mock_prep_os)
    assert mock_prep_os.wait_for_port.call_args == mock.call(22, result)


def test_get_port_timeout_uses_env(do_tests, Config):
    env = {
        'nova': {
            'flavor': 'some flavor'
        },
        'tests': {
            'port_wait_timeout': 42
        }
    }
    image = {
        'tests': {
            'tests_list': [],
            'wait_for_port': 22
        }
    }
    dt = do_tests.DoTests(Config(image), Config(env))
    mock_prep_os = mock.MagicMock()
    dt.wait_port(mock_prep_os)
    assert mock_prep_os.wait_for_port.call_args == mock.call(22, 42)


def test_get_port_timeout_uses_img(do_tests, Config):
    env = {
        'nova': {
            'flavor': 'some flavor'
        },
    }
    image = {
        'tests': {
            'tests_list': [],
            'wait_for_port': 22,
            'port_wait_timeout': 42
        }
    }
    dt = do_tests.DoTests(Config(image), Config(env))
    mock_prep_os = mock.MagicMock()
    dt.wait_port(mock_prep_os)
    assert mock_prep_os.wait_for_port.call_args == mock.call(22, 42)


def test_get_port_timeout_uses_default(do_tests):
    env = {
        'nova': {
            'flavor': 'some flavor'
        },
    }
    image = {
        'tests': {
            'tests_list': [],
            'wait_for_port': 22
        }
    }
    dt = do_tests.DoTests(image, env)
    mock_prep_os = mock.MagicMock()
    dt.wait_port(mock_prep_os)
    assert mock_prep_os.wait_for_port.call_args == mock.call(22, 61)  # magical constant!


def test_wait_port_no_port(do_tests):
    env = {
        'nova': {
            'flavor': 'some flavor'
        }
    }
    image = {
        'tests': {
            'tests_list': [],
        }
    }
    dt = do_tests.DoTests(image, env)
    mock_prep_os = mock.MagicMock()
    assert dt.wait_port(mock_prep_os) is False


def test_wait_port_timeout(do_tests):
    env = {
        'nova': {
            'flavor': 'some flavor'
        }
    }
    image = {
        'tests': {
            'tests_list': [],
            'wait_for_port': 42
        }
    }
    dt = do_tests.DoTests(image, env)
    mock_prep_os = mock.MagicMock()
    mock_prep_os.wait_for_port.return_value = False
    with pytest.raises(do_tests.TestError):
        dt.wait_port(mock_prep_os)


@pytest.mark.parametrize('port', [False, 22])
def test_process_minimal(do_tests, port, capsys):
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
        assert dt.process(False, False) is True
    assert 'passed' in capsys.readouterr()[0]


def refactor_test_process_port_timeout(do_tests):
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
            dt.process(False, False)


def test_process_with_tests(do_tests, capsys):
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
            assert dt.process(False, False) is True


def test_process_shell_only(do_tests, capsys):
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
    with mock.patch.object(do_tests.prepare_os, "PrepOS"):
        with mock.patch.object(do_tests.DoTests, "open_shell", return_value=sentinel.result):
            dt = do_tests.DoTests(image, env)
            assert dt.process(shell_only=True, shell_on_errors=False) == sentinel.result


def test_process_all_tests_fail(do_tests, capsys, Config):
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
    dt = do_tests.DoTests(Config(image), Config(env))
    dt.ssh = mock.MagicMock()
    with mock.patch.object(do_tests.pytest_runner, "runner") as runner:
        runner.side_effect = [False, ValueError("Shouldn't be called")]
        with mock.patch.object(do_tests.prepare_os, "PrepOS") as mock_prep_os_class:
            mock_prep_os = mock.MagicMock()
            mock_enter = mock.MagicMock()
            mock_enter.__enter__.return_value = mock_prep_os
            mock_prep_os_class.return_value = mock_enter
            assert dt.process(False, False) is False
            assert runner.call_count == 1


def test_process_all_tests_fail_open_shell(do_tests, Config):
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
    dt = do_tests.DoTests(Config(image), Config(env))
    dt.ssh = mock.MagicMock()
    with mock.patch.object(do_tests.pytest_runner, "runner") as runner:
        runner.side_effect = [False, ValueError("Shouldn't be called")]
        with mock.patch.object(do_tests.prepare_os, "PrepOS") as mock_prep_os_class:
            mock_prep_os = mock.MagicMock()
            mock_enter = mock.MagicMock()
            mock_enter.__enter__.return_value = mock_prep_os
            mock_prep_os_class.return_value = mock_enter
            with mock.patch.object(dt, 'open_shell') as mock_open_shell:
                assert dt.process(False, shell_on_errors=True) is False
                assert mock_open_shell.called


@pytest.mark.parametrize('result', [True, False])
def test_run_all_tests(do_tests, result, Config):
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
    with mock.patch.object(do_tests.DoTests, "run_test", return_value=result):
        dt = do_tests.DoTests(Config(image), Config(env))
        dt.ssh = mock.MagicMock()
        assert dt.run_all_tests(mock.MagicMock()) is result


@pytest.mark.parametrize('retval, keep', [
    [0, False],
    [1, False],
    [42, True]
])
def test_open_shell(do_tests, retval, keep):
    env = {
        'nova': {
            'flavor': 'some flavor'
        }
    }
    image = {
        'tests': {
            'ssh': {'username': 'user'},
            'wait_for_port': 22,
            'tests_list': [{'pytest': sentinel.path1}, {'pytest': sentinel.path2}]
        }
    }
    dt = do_tests.DoTests(image, env)
    mock_ssh = mock.MagicMock()
    mock_ssh.shell.return_value = retval
    dt.open_shell(mock_ssh, 'reason')
    assert dt.keep_failed_instance == keep
    assert 'exit 42' in mock_ssh.shell.call_args[0][1]


def test_open_shell_no_ssh_config(do_tests):
    env = {
        'nova': {
            'flavor': 'some flavor'
        }
    }
    image = {
    }
    dt = do_tests.DoTests(image, env)
    with pytest.raises(do_tests.TestError):
        dt.open_shell(None, 'reason')


@pytest.mark.parametrize('kins', [True, False])
@pytest.mark.parametrize('kimg', [True, False])
def test_check_if_keep_stuff_after_fail_code_coverage(do_tests, kins, kimg):
    env = {
        'nova': {
            'flavor': 'some flavor'
        },
    }
    image = {
        'tests': {
            'tests_list': [],
            'wait_for_port': 22
        }
    }
    dt = do_tests.DoTests(image, env)
    dt.keep_failed_instance = kins
    dt.keep_failed_image = kimg
    dt.check_if_keep_stuff_after_fail(mock.MagicMock())


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
