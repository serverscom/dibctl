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


@pytest.mark.parametrize('host, port, user, output', [
    ['192.168.1.1', 22, 'user', 'user@192.168.1.1'],
    ['192.168.1.1', 1222, 'user', 'user@192.168.1.1:1222']
])
def test_user_host_and_port(ssh, host, port, user, output):
    s = ssh.SSH(host, user, None, port)
    assert s.user_host_and_port() == output


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
