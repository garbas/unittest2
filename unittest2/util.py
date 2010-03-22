"""Various utility functions."""
import signal


__unittest = True


def safe_repr(obj):
    try:
        return repr(obj)
    except Exception:
        return object.__repr__(obj)

def safe_str(obj):
    try:
        return str(obj)
    except Exception:
        return object.__str__(obj)

def strclass(cls):
    return "%s.%s" % (cls.__module__, cls.__name__)

def sorted_list_difference(expected, actual):
    """Finds elements in only one or the other of two, sorted input lists.

    Returns a two-element tuple of lists.    The first list contains those
    elements in the "expected" list but not in the "actual" list, and the
    second contains those elements in the "actual" list but not in the
    "expected" list.    Duplicate elements in either input list are ignored.
    """
    i = j = 0
    missing = []
    unexpected = []
    while True:
        try:
            e = expected[i]
            a = actual[j]
            if e < a:
                missing.append(e)
                i += 1
                while expected[i] == e:
                    i += 1
            elif e > a:
                unexpected.append(a)
                j += 1
                while actual[j] == a:
                    j += 1
            else:
                i += 1
                try:
                    while expected[i] == e:
                        i += 1
                finally:
                    j += 1
                    while actual[j] == a:
                        j += 1
        except IndexError:
            missing.extend(expected[i:])
            unexpected.extend(actual[j:])
            break
    return missing, unexpected

def unorderable_list_difference(expected, actual, ignore_duplicate=False):
    """Same behavior as sorted_list_difference but
    for lists of unorderable items (like dicts).

    As it does a linear search per item (remove) it
    has O(n*n) performance.
    """
    missing = []
    unexpected = []
    while expected:
        item = expected.pop()
        try:
            actual.remove(item)
        except ValueError:
            missing.append(item)
        if ignore_duplicate:
            for lst in expected, actual:
                try:
                    while True:
                        lst.remove(item)
                except ValueError:
                    pass
    if ignore_duplicate:
        while actual:
            item = actual.pop()
            unexpected.append(item)
            try:
                while True:
                    actual.remove(item)
            except ValueError:
                pass
        return missing, unexpected

    # anything left in actual is unexpected
    return missing, actual


class InterruptHandler(object):
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
_interrupt_handler = None
def install_handler(result):
    global _interrupt_handler
    if _interrupt_handler is None:
        default_handler = signal.getsignal(signal.SIGINT)
        _interrupt_handler = InterruptHandler(default_handler)
        signal.signal(signal.SIGINT, _interrupt_handler)
    
    _results.add(result)

    
