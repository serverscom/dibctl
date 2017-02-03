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
    def test_handler(signum, frame, timeout=True):
        raise ValueError("It's ok")
    with pytest.raises(ValueError):
        with timeout.timeout(1, test_handler):
            import time
            time.sleep(2)
            raise Exception("Test failed, no alarm call")


def test_timeout_after_exception(timeout):
    # based on real bug: alarm wasn't cleared after error handler
    with timeout.timeout(1, mock.MagicMock(side_effect=[
        ValueError,
        EnvironmentError ("This exception shouldn't be raised")
    ])):
        with pytest.raises(ValueError):
            raise ValueError
    time.sleep(2)


def test_timeout_check_clear_alarm(timeout):
    with mock.patch.object(timeout, "signal") as mock_signal:
        with timeout.timeout(sentinel.timeout, sentinel.handler):
            assert mock_signal.alarm.call_args[0][0] == sentinel.timeout
        assert mock_signal.alarm.call_args[0][0] == 0


def test_timeout_check_no_error(timeout):
    def test_handler(signum, frame, timeout=True):
        raise ValueError("Shouldn't be called, timeout happens!")
    with timeout.timeout(1, test_handler):
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
