import signal
import weakref

__unittest = True


class _InterruptHandler(object):
    def __init__(self, default_handler):
        self.called = False
        self.default_handler = default_handler

    def __call__(self, signum, frame):
        if self.called:
            self.default_handler(signum, frame)
        self.called = True
        for result in _results:
            result.stop()

_results = set()
def registerResult(result):
    _results.add(result)

_interrupt_handler = None
def installHandler():
    global _interrupt_handler
    if _interrupt_handler is None:
        default_handler = signal.getsignal(signal.SIGINT)
        _interrupt_handler = _InterruptHandler(default_handler)
        signal.signal(signal.SIGINT, _interrupt_handler)
