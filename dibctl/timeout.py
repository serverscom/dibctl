import signal


class timeout(object):
    def __init__(self, timeout, handler):
        self.timeout = timeout
        self.handler = handler

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handler)
        signal.alarm(self.timeout)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signal.alarm(0)
