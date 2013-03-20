import sys
import warnings

import unittest2


def resultFactory(*_):
    return unittest2.TestResult()

class OldTestResult(object):
    """An object honouring TestResult before startTestRun/stopTestRun."""

    def __init__(self, *_):
        self.failures = []
        self.errors = []
        self.testsRun = 0
        self.shouldStop = False

    def startTest(self, test):
        # so this fake TestResult can still count tests
        self.testsRun += 1

    def stopTest(self, test):
        pass

    def addError(self, test, err):
        self.errors.append((test, err))

    def addFailure(self, test, err):
        self.failures.append((test, err))

    def addSuccess(self, test):
        pass

    def wasSuccessful(self):
        return True

    def printErrors(self):
        pass

class _BaseLoggingResult(unittest2.TestResult):
    def __init__(self, log):
        self._events = log
        super(_BaseLoggingResult, self).__init__()

    def startTest(self, test):
        self._events.append('startTest')
        super(_BaseLoggingResult, self).startTest(test)

    def startTestRun(self):
        self._events.append('startTestRun')
        super(_BaseLoggingResult, self).startTestRun()

    def stopTest(self, test):
        self._events.append('stopTest')
        super(_BaseLoggingResult, self).stopTest(test)

    def stopTestRun(self):
        self._events.append('stopTestRun')
        super(_BaseLoggingResult, self).stopTestRun()

    def addFailure(self, *args):
        self._events.append('addFailure')
        super(_BaseLoggingResult, self).addFailure(*args)

    def addSuccess(self, *args):
        self._events.append('addSuccess')
        super(_BaseLoggingResult, self).addSuccess(*args)

    def addError(self, *args):
        self._events.append('addError')
        super(_BaseLoggingResult, self).addError(*args)

    def addSkip(self, *args):
        self._events.append('addSkip')
        super(_BaseLoggingResult, self).addSkip(*args)

    def addExpectedFailure(self, *args):
        self._events.append('addExpectedFailure')
        super(_BaseLoggingResult, self).addExpectedFailure(*args)

    def addUnexpectedSuccess(self, *args):
        self._events.append('addUnexpectedSuccess')
        super(_BaseLoggingResult, self).addUnexpectedSuccess(*args)


class LegacyLoggingResult(_BaseLoggingResult):
    """
    A legacy TestResult implementation, without an addSubTest method,
    which records its method calls.
    """

    @property
    def addSubTest(self):
        raise AttributeError


class LoggingResult(_BaseLoggingResult):
    """
    A TestResult implementation which records its method calls.
    """

    def addSubTest(self, test, subtest, err):
        if err is None:
            self._events.append('addSubTestSuccess')
        else:
            self._events.append('addSubTestFailure')
        super(LoggingResult, self).addSubTest(test, subtest, err)


class EqualityMixin(object):
    """Used as a mixin for TestCase"""

    # Check for a valid __eq__ implementation
    def test_eq(self):
        for obj_1, obj_2 in self.eq_pairs:
            self.assertEqual(obj_1, obj_2)
            self.assertEqual(obj_2, obj_1)

    # Check for a valid __ne__ implementation
    def test_ne(self):
        for obj_1, obj_2 in self.ne_pairs:
            self.assertNotEqual(obj_1, obj_2)
            self.assertNotEqual(obj_2, obj_1)

class HashingMixin(object):
    """Used as a mixin for TestCase"""

    # Check for a valid __hash__ implementation
    def test_hash(self):
        for obj_1, obj_2 in self.eq_pairs:
            try:
                if not hash(obj_1) == hash(obj_2):
                    self.fail("%r and %r do not hash equal" % (obj_1, obj_2))
            except KeyboardInterrupt:
                raise
            except Exception:
                e = sys.exc_info()[1]
                self.fail("Problem hashing %r and %r: %s" % (obj_1, obj_2, e))

        for obj_1, obj_2 in self.ne_pairs:
            try:
                if hash(obj_1) == hash(obj_2):
                    self.fail("%s and %s hash equal, but shouldn't" %
                              (obj_1, obj_2))
            except KeyboardInterrupt:
                raise
            except Exception:
                e = sys.exc_info()[1]
                self.fail("Problem hashing %s and %s: %s" % (obj_1, obj_2, e))

