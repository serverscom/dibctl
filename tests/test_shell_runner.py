#!/usr/bin/python
import mock
import pytest
import os
import inspect
import sys
from mock import sentinel
import tempfile
import uuid


@pytest.fixture
def ssh():
    from dibctl import ssh
    return ssh


@pytest.fixture
def shell_runner():
    from dibctl import shell_runner
    return shell_runner


@pytest.mark.parametrize("input, output", [
    [[], {}],
    [{}, {}],
    [None, {}],
    ["foo", {"P": "foo"}],
    [1, {"P": "1"}],
    [True, {"P": "True"}],
    [{"sublevel": "value"}, {"P_SUBLEVEL": "value"}],
    [{1: "value"}, {"P_1": "value"}],
    [{"one": "value", "two": "value"}, {"P_ONE": "value", "P_TWO": "value"}],
    [[{"one": "value"}, {"two": "value"}], {"P_ONE": "value", "P_TWO": "value"}],
    [{"sublevel1": {"sublevel2": "value"}}, {"P_SUBLEVEL1_SUBLEVEL2": "value"}],
    [{"one": "foo", "sublevel1": {"sublevel2": "value"}}, {"P_SUBLEVEL1_SUBLEVEL2": "value", "P_ONE": "foo"}],
    [{"one": ["foo", "bar"]}, {"P_ONE": "bar"}],  # invalid
])
def test_unwrap_config(shell_runner, input, output):
    assert shell_runner.unwrap_config("P", input) == output


def test_run_shell_test_success(shell_runner):
    with mock.patch.object(shell_runner.subprocess, "check_call", autospec=True) as mock_call:
        assert shell_runner.run_shell_test(sentinel.path, sentinel.evn)


def test_run_shell_test_fail(shell_runner):
    with mock.patch.object(shell_runner.subprocess, "check_call") as mock_call:
        mock_call.side_effect = shell_runner.subprocess.CalledProcessError(0, [], "")
        assert shell_runner.run_shell_test(sentinel.path, sentinel.evn) is False


def test_gather_tests_bad_file(shell_runner):
    assert shell_runner.gather_tests('/dev/null') is None


def test_gather_tests_single_file_no_exec(shell_runner):
    ftmp = tempfile.NamedTemporaryFile(delete=False)
    os.chmod(ftmp.name, 0o600)
    assert shell_runner.gather_tests(ftmp.name) is None
    ftmp.close()
    os.remove(ftmp.name)


def test_gather_tests_single_file_exec(shell_runner):
    ftmp = tempfile.NamedTemporaryFile(delete=False)
    os.chmod(ftmp.name, 0o700)
    assert shell_runner.gather_tests(ftmp.name) == ftmp.name
    ftmp.close()
    os.remove(ftmp.name)


def test_gather_tests_single_file_exec(shell_runner):
    uuid1 = str(uuid.uuid4())
    uuid2 = str(uuid.uuid4())
    uuid3 = str(uuid.uuid4())
    tdir = tempfile.mkdtemp()
    tdir2 = os.path.join(tdir, uuid1)
    tdir3 = os.path.join(tdir2, uuid3)
    os.mkdir(tdir2)
    os.mkdir(tdir3)
    tmp1 = os.path.join(tdir, uuid2)
    tmp2 = os.path.join(tdir3, uuid3)
    open(tmp1, 'w').write('pytest')
    open(tmp2, 'w').write('pytest')
    os.chmod(tmp1, 0o600)
    os.chmod(tmp2, 0o700)
    assert shell_runner.gather_tests(tdir) == [tmp2]
    os.remove(tmp1)
    os.remove(tmp2)
    os.rmdir(tdir3)
    os.rmdir(tdir2)
    os.rmdir(tdir)


def test_runner_bad_path(shell_runner):
    with pytest.raises(shell_runner.BadRunnerError):
        shell_runner.runner('/dev/null', sentinel.ssh, sentinel.config, sentinel.vars, sentinel.timeout, continue_on_fail=False)


def test_runner_empty_tests(shell_runner, ssh):
    tos = mock.MagicMock()
    tos.ip = '192.168.1.1'
    tos.os_key_private_file = '~/.ssh/config'
    vars = {}
    s = ssh.SSH('192.168.1.1', 'user', 'secret')
    with mock.patch.object(shell_runner, "gather_tests", return_value=[]):
        assert shell_runner.runner(sentinel.path, s, tos, vars, sentinel.timeout, continue_on_fail=False) is True
    del s


def test_runner_all_ok(shell_runner, ssh):
    tos = mock.MagicMock()
    tos.ip = '192.168.1.1'
    tos.os_key_private_file = '~/.ssh/config'
    vars = {}
    with mock.patch.object(shell_runner, "gather_tests", return_value=["test1", "test2"]):
        with mock.patch.object(shell_runner, "run_shell_test", return_value=True):
            s = ssh.SSH('192.168.1.1', 'user', 'secret')
            assert shell_runner.runner(sentinel.path, s, tos, vars, sentinel.timeout, continue_on_fail=False) is True
            del s


def test_runner_all_no_continue(shell_runner, ssh):
    tos = mock.MagicMock()
    tos.ip = '192.168.1.1'
    tos.os_key_private_file = '~/.ssh/config'
    vars = {}
    s = ssh.SSH('192.168.1.1', 'user', 'secret')
    with mock.patch.object(shell_runner, "gather_tests", return_value=["test1", "test2"]):
        with mock.patch.object(shell_runner, "run_shell_test", return_value=False) as mock_run:
            assert shell_runner.runner(sentinel.path, s, tos, vars, sentinel.timeout, continue_on_fail=False) is False
            assert mock_run.call_count == 1
    del s


def test_runner_all_with_continue(shell_runner, ssh):
    tos = mock.MagicMock()
    tos.ip = '192.168.1.1'
    tos.os_key_private_file = '~/.ssh/config'
    vars = {}
    s = ssh.SSH('192.168.1.1', 'user', 'secret')
    with mock.patch.object(shell_runner, "gather_tests", return_value=["test1", "test2"]):
        with mock.patch.object(shell_runner, "run_shell_test", return_value=False) as mock_run:
            assert shell_runner.runner(sentinel.path, s, tos, vars, sentinel.timeout, continue_on_fail=True) is False
            assert mock_run.call_count == 2
    del s


if __name__ == "__main__":
    ourfilename = os.path.abspath(inspect.getopen(inspect.currentframe()))
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
