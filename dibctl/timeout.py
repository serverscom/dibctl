import signal


class TimeoutError(EnvironmentError):
    pass


class timeout(object):
    def __init__(self, timeout):
        self.timeout = timeout

    def raise_timeout(self, signum, frame):
        if signum == signal.SIGALRM:
            raise TimeoutError("Timed out after %s" % self.timeout)
        else:
            raise RuntimeError("Signal %s, have no idea what to do" % signum)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.raise_timeout)
        signal.alarm(self.timeout)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signal.alarm(0)
