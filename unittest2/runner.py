"""Running tests"""

import sys
import time
import unittest

from unittest2 import result
from unittest2.events import (
    hooks, StartTestRunEvent, StopTestRunEvent,
    RunnerCreatedEvent
)

try:
    from unittest2.signals import registerResult
except ImportError:
    def registerResult(_):
        pass
    
__unittest = True

_messages = []
_runner = None
def setRunner(runner):
    """
    Set the default TestRunner used by the `message` function. Set the runner
    to None to queue messages or to allow the default TestRunner to be freed.

    If there are any messages queued then they will be output on the runner by
    calling its `message` method.

    If the default runner is None instantiating a `TextTestRunner` will set the
    default runner.
    """
    global _runner
    _runner = runner

    if runner is None:
        return
    
    for message, verbosity in _messages:
        runner.message(message, verbosity)

def message(message, verbosity=(1, 2)):
    """
    Output a `message` to the stream set on the default TestRunner. 

    `verbosity` should be 0, 1 or 2. The `message` will only be output if it
    *matches* the verbosity set on the runner. If you wish the message to be
    output for several verbosity settings you may pass in a tuple of
    verbosities.

    For example this call outputs the message for verbosities of 1 *and* 2::

        message('Important message', (1, 2))

    The default verbosity is (1, 2). If this function is called without
    an explicit verbosity it will be output for verbosities of both 1 and 2.

    `message` will be output verbatim; newlines are not added.

    If no runner has been created, the messages are queued until one is created
    or set with `setRunner`.
    """
    try:
        iter(verbosity)
    except TypeError:
        pass
    else:
        for verb in verbosity:
            message(message, verb)
        return

    if _runner is None:
        _messages.append((message, verbosity))
    else:
        _runner.message(message, verbosity)


class _WritelnDecorator(object):
    """Used to decorate file-like objects with a handy 'writeln' method"""
    def __init__(self,stream):
        self.stream = stream

    def __getattr__(self, attr):
        if attr in ('stream', '__getstate__'):
            raise AttributeError(attr)
        return getattr(self.stream,attr)

    def writeln(self, arg=None):
        if arg:
            self.write(arg)
        self.write('\n') # text-mode streams translate to \r\n if needed


class TextTestResult(result.TestResult):
    """A test result class that can print formatted text results to a stream.

    Used by TextTestRunner.
    """
    separator1 = '=' * 70
    separator2 = '-' * 70

    def __init__(self, stream, descriptions, verbosity):
        super(TextTestResult, self).__init__()
        self.stream = stream
        self.showAll = verbosity > 1
        self.dots = verbosity == 1
        self.descriptions = descriptions

    def getDescription(self, test):
        doc_first_line = test.shortDescription()
        if self.descriptions and doc_first_line:
            return '\n'.join((str(test), doc_first_line))
        else:
            return str(test)

    def startTest(self, test):
        super(TextTestResult, self).startTest(test)
        if self.showAll:
            self.stream.write(self.getDescription(test))
            self.stream.write(" ... ")
            self.stream.flush()

    def addSuccess(self, test):
        super(TextTestResult, self).addSuccess(test)
        if self.showAll:
            self.stream.writeln("ok")
        elif self.dots:
            self.stream.write('.')
            self.stream.flush()

    def addError(self, test, err):
        super(TextTestResult, self).addError(test, err)
        if self.showAll:
            self.stream.writeln("ERROR")
        elif self.dots:
            self.stream.write('E')
            self.stream.flush()

    def addFailure(self, test, err):
        super(TextTestResult, self).addFailure(test, err)
        if self.showAll:
            self.stream.writeln("FAIL")
        elif self.dots:
            self.stream.write('F')
            self.stream.flush()

    def addSkip(self, test, reason):
        super(TextTestResult, self).addSkip(test, reason)
        if self.showAll:
            self.stream.writeln("skipped %r" % (reason,))
        elif self.dots:
            self.stream.write("s")
            self.stream.flush()

    def addExpectedFailure(self, test, err):
        super(TextTestResult, self).addExpectedFailure(test, err)
        if self.showAll:
            self.stream.writeln("expected failure")
        elif self.dots:
            self.stream.write("x")
            self.stream.flush()

    def addUnexpectedSuccess(self, test):
        super(TextTestResult, self).addUnexpectedSuccess(test)
        if self.showAll:
            self.stream.writeln("unexpected success")
        elif self.dots:
            self.stream.write("u")
            self.stream.flush()

    def printErrors(self):
        if self.dots or self.showAll:
            self.stream.writeln()
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            self.stream.writeln(self.separator1)
            self.stream.writeln("%s: %s" % (flavour, self.getDescription(test)))
            self.stream.writeln(self.separator2)
            self.stream.writeln("%s" % err)

    def stopTestRun(self):
        super(TextTestResult, self).stopTestRun()
        self.printErrors()


class TextTestRunner(unittest.TextTestRunner):
    """A test runner class that displays results in textual form.

    It prints out the names of tests as they are run, errors as they
    occur, and a summary of the results at the end of the test run.
    """
    resultclass = TextTestResult

    def __init__(self, stream=sys.stderr, descriptions=True, verbosity=1,
                    failfast=False, buffer=False, resultclass=None):
        self.stream = _WritelnDecorator(stream)
        
        self.descriptions = descriptions
        self.verbosity = verbosity
        self.failfast = failfast
        self.buffer = buffer
        if resultclass is not None:
            self.resultclass = resultclass
            
        event = RunnerCreatedEvent(self)
        hooks.runnerCreated(event)
        
        if _runner is None:
            setRunner(self)

    def message(self, message, verbosity=(1, 2)):
        """
        Output a `message` to the stream if the `verbosity` *matches* the
        verbosity of the runner.
        
        `verbosity` can be a single value or a tuple of values. If `verbosity`
        is a tuple of values then the message will be written to the stream
        if any of the values match the runner verbosity.

        
        The default verbosity is (1, 2). If this method is called without an
        explicit verbosity it will be output for verbosities of both 1 and 2.
        """
        try:
            iter(verbosity)
        except TypeError:
            verbosity = (verbosity,)
        
        for verb in verbosity:
            if verb == self.verbosity:
                self.stream.write(message)
                break

    def _makeResult(self):
        return self.resultclass(self.stream, self.descriptions, self.verbosity)

    def run(self, test):
        "Run the given test case or test suite."
        result = self._makeResult()
        result.failfast = self.failfast
        result.buffer = self.buffer
        registerResult(result)
        
        startTime = time.time()
        startTestRun = getattr(result, 'startTestRun', None)
        if startTestRun is not None:
            startTestRun()
        
        event = StartTestRunEvent(self, test, result, startTime)
        hooks.startTestRun(event)
        # allows startTestRun to modify test suite
        test = event.suite
        try:
            if not event.handled:
                test(result)
        finally:
            stopTestRun = getattr(result, 'stopTestRun', None)
            if stopTestRun is not None:
                stopTestRun()
            else:
                result.printErrors()
        
            stopTime = time.time()
            timeTaken = stopTime - startTime
            
            event = StopTestRunEvent(self, result, stopTime, timeTaken)
            hooks.stopTestRun(event)

        if hasattr(result, 'separator2'):
            self.stream.writeln(result.separator2)
        run = result.testsRun
        self.stream.writeln("Ran %d test%s in %.3fs" %
                            (run, run != 1 and "s" or "", timeTaken))
        self.stream.writeln()
        
        expectedFails = unexpectedSuccesses = skipped = 0
        try:
            results = map(len, (result.expectedFailures,
                                result.unexpectedSuccesses,
                                result.skipped))
            expectedFails, unexpectedSuccesses, skipped = results
        except AttributeError:
            pass
        infos = []
        if not result.wasSuccessful():
            self.stream.write("FAILED")
            failed, errored = map(len, (result.failures, result.errors))
            if failed:
                infos.append("failures=%d" % failed)
            if errored:
                infos.append("errors=%d" % errored)
        else:
            self.stream.write("OK")
        if skipped:
            infos.append("skipped=%d" % skipped)
        if expectedFails:
            infos.append("expected failures=%d" % expectedFails)
        if unexpectedSuccesses:
            infos.append("unexpected successes=%d" % unexpectedSuccesses)
        if infos:
            self.stream.writeln(" (%s)" % (", ".join(infos),))
        else:
            self.stream.write("\n")
        return result
