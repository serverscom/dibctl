import pytest
from mock import sentinel


class MockSock(object):

    def __init__(self, sequence):
        self.sequence = sequence

    AF_INET = sentinel.AF_INET
    SOCK_STREAM = sentinel.SOCK_STREAM

    def socket(self, arg1, arg2):
        assert arg1 is self.AF_INET
        assert arg2 is self.SOCK_STREAM
        return self

    def connect_ex(self, ip):
        next = self.sequence[0]
        if next is None:
            return -1  # Loop forever with None
        self.sequence = self.sequence[1:]
        return next


@pytest.fixture(scope="module")
def MockSocket(request):
    return MockSock
