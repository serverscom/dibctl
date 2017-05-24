#!/usr/bin/python
import os
import inspect
import sys
import pytest
import mock
import time
from mock import sentinel


@pytest.fixture
def timeout():
    from dibctl import timeout
    return timeout


def test_timeout_real_timeout(timeout):
    with pytest.raises(timeout.TimeoutError):
        with timeout.timeout(1):
            import time
            time.sleep(2)


def test_timeout_after_exception(timeout):
    # based on real bug: alarm wasn't cleared after error handler
    with pytest.raises(ValueError):
        with timeout.timeout(1):
            raise ValueError
    time.sleep(2)


def test_timeout_check_no_error(timeout):
    with timeout.timeout(1):
        pass


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
