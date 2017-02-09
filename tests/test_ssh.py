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
