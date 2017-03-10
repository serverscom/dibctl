#!/usr/bin/python
import os
import inspect
import sys
import pytest
import mock
from mock import sentinel


@pytest.fixture
def ssh():
    from dibctl import ssh
    return ssh


@pytest.mark.parametrize('ip, port, user, output', [
    ['192.168.1.1', 22, 'user', 'user@192.168.1.1'],
    ['192.168.1.1', 1222, 'user', 'user@192.168.1.1:1222']
])
def test_user_host_and_port(ssh, ip, port, user, output):
    s = ssh.SSH(ip, user, None, port)
    assert s.user_host_and_port() == output


def test_key_file(ssh):
    with mock.patch.object(ssh.tempfile, 'NamedTemporaryFile') as mock_tmp:
        mock_tmp.return_value.name = sentinel.filename
        s = ssh.SSH(sentinel.ip, sentinel.user, "secret", sentinel.port)
        assert s.key_file() == sentinel.filename
        assert mock_tmp.return_value.write.call_args == mock.call('secret')


def test_key_file_name(ssh):
    s = ssh.SSH(sentinel.ip, sentinel.user, "secret", sentinel.port)
    f = s.key_file()
    assert 'dibctl_key' in f


def test_key_file_content(ssh):
    s = ssh.SSH(sentinel.ip, sentinel.user, "secret", sentinel.port)
    f = s.key_file()
    assert open(f, 'r').read() == "secret"


def test_key_file_remove_afterwards(ssh):
    s = ssh.SSH(sentinel.ip, sentinel.user, "secret", sentinel.port)
    f = s.key_file()
    del s
    with pytest.raises(IOError):
        open(f, 'r')


def test_keep_key_file_name(ssh):
    s = ssh.SSH(sentinel.ip, sentinel.user, "secret", sentinel.port)
    f = s.keep_key_file()
    assert 'saved_dibctl_key_' in f
    os.remove(f)


def test_keep_key_file_content(ssh):
    s = ssh.SSH(sentinel.ip, sentinel.user, "secret", sentinel.port)
    f = s.keep_key_file()
    assert 'secret' in open(f, 'r').read()
    os.remove(f)


def test_keep_key_file_kept_after_removal(ssh):
    s = ssh.SSH(sentinel.ip, sentinel.user, "secret", sentinel.port)
    f = s.keep_key_file()
    del s
    assert 'secret' in open(f, 'r').read()
    os.remove(f)


def test_command_line(ssh):
    s = ssh.SSH('192.168.0.1', 'user', 'secret')
    cmdline = " ".join(s.command_line())
    assert 'user@192.168.0.1' in cmdline
    assert "-o StrictHostKeyChecking=no" in cmdline
    assert "-o UserKnownHostsFile=/dev/null" in cmdline
    assert "-o UpdateHostKeys=no" in cmdline
    assert "-o PasswordAuthentication=no" in cmdline
    assert "-i " in cmdline
    del s


def test_connector(ssh):
    s = ssh.SSH('192.168.0.1', sentinel.user, sentinel.key)
    assert s.connector() == 'ssh://192.168.0.1'


def test_config_name(ssh):
    s = ssh.SSH('192.168.0.1', 'user', 'secret')
    assert 'dibctl_config_' in s.config()
    del s


def test_config_content(ssh):
    s = ssh.SSH('192.168.0.1', 'user', 'secret', port=99)
    cfg = s.config()
    with open(cfg, 'r') as c:
        data = c.read()
        assert "User user" in data
        assert "Host 192.168.0.1" in data
        assert "StrictHostKeyChecking no" in data
        assert "UserKnownHostsFile /dev/null" in data
        assert "UpdateHostKeys no" in data
        assert "PasswordAuthentication no" in data
        assert "Port 99" in data
        assert "IdentityFile" in data
    del s


def test_config_afterwards(ssh):
    s = ssh.SSH('192.168.0.1', 'user', 'secret')
    cfg = s.config()
    del s
    with pytest.raises(IOError):
        open(cfg, 'r')


def test_env_vars(ssh):
    s = ssh.SSH('192.168.0.1', 'user', 'secret')
    env = s.env_vars('TEST_')
    assert env['TEST_SSH_USERNAME'] == 'user'
    assert env['TEST_SSH_IP'] == '192.168.0.1'
    assert env['TEST_SSH_PORT'] == '22'
    assert open(env['TEST_SSH_PRIVATE_KEY'], 'r').read() == 'secret'
    assert "Host" in open(env['TEST_SSH_CONFIG'], 'r').read()
    assert "192.168.0.1" in env['TEST_SSH']
    del s


def test_shell_simple_run(ssh):
    with mock.patch.object(ssh.SSH, "COMMAND_NAME", "echo"):
        s = ssh.SSH('192.168.0.1', 'user', 'secret')
        rfd, wfd = os.pipe()
        w = os.fdopen(wfd, 'w', 0)
        with mock.patch.multiple(ssh.sys, stdout=w, stderr=w, stdin=None):
            s.shell({}, 'test message')
        output = os.read(rfd, 1000)
        assert 'echo' in output #  should be ssh, but test demands
        assert 'user@192.168.0.1' in output


@pytest.mark.parametrize('key, value', [
    ['ip', '192.168.0.1'],
    ['username', 'user'],
    ['port', 22]
])
def test_info(ssh, key, value):
    s = ssh.SSH('192.168.0.1', 'user', 'secret')
    i = s.info()
    assert i[key] == value
    del s


@pytest.mark.parametrize('key', [
    'config',
    'private_key_file',
    'config',
    'command_line',
    'connector'
])
def test_info_2(ssh, key):
    s = ssh.SSH('192.168.0.1', 'user', 'secret')
    i = s.info()
    assert key in i
    del s


if __name__ == "__main__":
    ourfilename = os.path.abspath(inspect.getfile(inspect.currentframe()))
    currentdir = os.path.dirname(ourfilename)
    parentdir = os.path.dirname(currentdir)
    file_to_test = os.path.join(
        parentdir,
        os.path.basename(parentdir),
        os.path.basename(ourfilename).replace("test_", '')
    )
    pytest.main([
     "-vv",
     "--cov", file_to_test,
     "--cov-report", "term-missing"
     ] + sys.argv)
