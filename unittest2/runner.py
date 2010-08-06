"""Running tests"""

import sys
import time
import unittest

from unittest2 import result
from unittest2.events import (
    hooks, StartTestRunEvent, StopTestRunEvent,
    RunnerCreatedEvent, MessageEvent, ReportEvent
)

try:
    from unittest2.signals import registerResult
except ImportError:
    def registerResult(_):
        pass
    
__unittest = True

_messages = []
_runner = None

VERBOSITIES = { 'quiet': 0, 'normal': 1, 'verbose': 2}

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
    
    for msg, verbosity in _messages:
        runner.message(msg, verbosity)

def message(msg, verbosity=(1, 2)):
    """
    Output `msg` to the stream set on the default TestRunner. `msg` must be a
    string.

    `verbosity` should be 0, 1 or 2. The `message` will only be output if it
    *matches* the verbosity set on the runner. If you wish the message to be
    output for several verbosity settings you may pass in a tuple of
    verbosities.

    For example this call outputs the message for verbosities of 1 *and* 2::

        message('Important message', (1, 2))

    The default verbosity is (1, 2). If this function is called without
    an explicit verbosity it will be output for verbosities of both 1 and 2.

    `msg` will be output verbatim; newlines are not added.

    If no runner has been created, the messages are queued until one is created
    or set with `setRunner`.
    """
    if not isinstance(verbosity, basestring):
        # allow support for arbitrary channels later
        try:
            iter(verbosity)
        except TypeError:
            pass
        else:
            for verb in verbosity:
                message(msg, verb)
            return
    else:
        if verbosity.lower() in VERBOSITIES:
            verbosity = VERBOSITIES[verbosity]
    
    if _runner is None:
        _messages.append((msg, verbosity))
    else:
        _runner.message(msg, verbosity)


class _WritelnDecorator(object):
    """Used to decorate file-like objects with a handy 'writeln' method"""
    def __init__(self, stream, runner=None):
        self.stream = stream
        self.runner = runner

    def __getattr__(self, attr):
        if attr in ('stream', '__getstate__'):
            raise AttributeError(attr)
        return getattr(self.stream,attr)
    
    def write(self, arg):
        if self.runner:
            self.runner.message(arg, (0, 1, 2))
        else:
            self.stream.write(arg)

    def writeln(self, arg=None):
        if self.runner:
            arg = arg or ''
            self.runner.message(arg + '\n', (0, 1, 2))
            return

        if arg:
            self.stream.write(arg)
        self.stream.write('\n') # text-mode streams translate to \r\n if needed


class TextTestResult(result.TestResult):
    """A test result class that can print formatted text results to a stream.

    Used by TextTestRunner.
    """
    separator1 = '=' * 70
    separator2 = '-' * 70

    def __init__(self, stream, descriptions, verbosity):
        super(TextTestResult, self).__init__()
        self._reported = False
        self.stream = stream
        self.showAll = verbosity > 1
        self.dots = verbosity == 1
        self.descriptions = descriptions
        self.reportCategories = {}

    def getDescription(self, test):
        doc_first_line = test.shortDescription()
        if self.descriptions and doc_first_line:
            return '\n'.join((str(test), doc_first_line))
        else:
            return str(test)
    
    def addReport(self, report):
        self._reported = False
        super(TextTestResult, self).addReport(report)
        if self._reported:
            return
        if self.showAll:
            self.stream.writeln(report.longResult)
        elif self.dots:
            self.stream.write(report.shortResult)
            self.stream.flush()

        # remove references to test/result/exception from report
        report.clean()

    def startTest(self, test):
        self._reported = True
        super(TextTestResult, self).startTest(test)
        if self.showAll:
            self.stream.write(self.getDescription(test))
            self.stream.write(" ... ")
            self.stream.flush()

    def addSuccess(self, test):
        super(TextTestResult, self).addSuccess(test)
        self._reported = True
        if self.showAll:
            self.stream.writeln("ok")
        elif self.dots:
            self.stream.write('.')
            self.stream.flush()

    def addError(self, test, err):
        super(TextTestResult, self).addError(test, err)
        self._reported = True
        if self.showAll:
            self.stream.writeln("ERROR")
        elif self.dots:
            self.stream.write('E')
            self.stream.flush()

    def addFailure(self, test, err):
        super(TextTestResult, self).addFailure(test, err)
        self._reported = True
        if self.showAll:
            self.stream.writeln("FAIL")
        elif self.dots:
            self.stream.write('F')
            self.stream.flush()

    def addSkip(self, test, reason):
        super(TextTestResult, self).addSkip(test, reason)
        self._reported = True
        if self.showAll:
            self.stream.writeln("skipped %r" % reason)
        elif self.dots:
            self.stream.write("s")
            self.stream.flush()

    def addExpectedFailure(self, test, err):
        super(TextTestResult, self).addExpectedFailure(test, err)
        self._reported = True
        if self.showAll:
            self.stream.writeln("expected failure")
        elif self.dots:
            self.stream.write("x")
            self.stream.flush()

    def addUnexpectedSuccess(self, test):
        super(TextTestResult, self).addUnexpectedSuccess(test)
        self._reported = True
        if self.showAll:
            self.stream.writeln("unexpected success")
        elif self.dots:
            self.stream.write("u")
            self.stream.flush()

    def printErrors(self):
        if self.dots or self.showAll:
            self.stream.writeln()

        for report in self.reports:
            reportList = self.reportCategories.setdefault(report.outcome, [])
            reportList.append((report.description, report.traceback))
        
        errors = self.reportCategories.get('error', [])
        failures = self.reportCategories.get('failed', [])
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

        dontReport = set(['error', 'failed', 'skipped', 'passed',
                          'expectedFailures', 'unexpectedSuccess'])
        for flavour, results in self.reportCategories.items():
            if flavour in dontReport:
                continue
            self.printErrorList(flavour.upper(), results)

    def printErrorList(self, flavour, errors):
        for desc, err in errors:
            if not isinstance(desc, basestring):
                desc = self.getDescription(desc)
            self.stream.writeln(self.separator1)
            self.stream.writeln("%s: %s" % (flavour, desc))
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
        self.stream = _WritelnDecorator(stream, self)
        
        self.descriptions = descriptions
        if isinstance(verbosity, basestring):
            # allow string verbosities not in the dictionary
            # for backwards compatibility
            verbosity = VERBOSITIES.get(verbosity.lower(), verbosity)
        self.verbosity = verbosity
        self.failfast = failfast
        self.buffer = buffer
        if resultclass is not None:
            self.resultclass = resultclass
            
        event = RunnerCreatedEvent(self)
        hooks.runnerCreated(event)
        
        if _runner is None:
            setRunner(self)

    def message(self, msg, verbosity=(1, 2)):
        """
        Output `msg` to the stream if the `verbosity` *matches* the
        verbosity of the runner. `msg` must be a string.
        
        `verbosity` can be a single value or a tuple of values. If `verbosity`
        is a tuple of values then the message will be written to the stream
        if any of the values match the runner verbosity.

        
        The default verbosity is (1, 2). If this method is called without an
        explicit verbosity it will be output for verbosities of both 1 and 2.
        """
        stream = self.stream
        if hasattr(stream, 'stream'):
            # for _WritelnDecorator decorated streams
            stream = stream.stream

        if not isinstance(verbosity, basestring):
            try:
                iter(verbosity)
            except TypeError:
                verbosity = (verbosity,)
        else:
            verbosity = (verbosity,)

        def makeInt(verb):
            if isinstance(verb, basestring):
                return VERBOSITIES.get(verb.lower(), verb)
            return verb
        verbosity = tuple(makeInt(verb) for verb in verbosity)
        event = MessageEvent(self, self.stream, msg, verbosity)
        result = hooks.message(event)
        if event.handled:
            if result:
                self.stream.write(msg)
                self.stream.flush()
            return

        msg = event.message
        verbosity = event.verbosity
        for verb in verbosity:
            if isinstance(verb, basestring):
                # don't raise a KeyError here on unrecognised verbosities
                # as non-matched channels will be passed through here
                verb = VERBOSITIES.get(verb, verb)
            if verb == self.verbosity:
                stream.write(msg)
                stream.flush()
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
        
        executor = lambda suite, result: test(result)
        event = StartTestRunEvent(self, test, result, startTime, executor)
        hooks.startTestRun(event)
        
        # allows startTestRun to modify test suite
        test = event.suite
        executor = event.executeTests
        try:
            if not event.handled:
                executor(test, result)
        finally:
            stopTime = time.time()
            timeTaken = stopTime - startTime

            event = StopTestRunEvent(self, result, stopTime, timeTaken)
            hooks.stopTestRun(event)

            stopTestRun = getattr(result, 'stopTestRun', None)
            if stopTestRun is not None:
                stopTestRun()
            else:
                result.printErrors()

        reportEvent = ReportEvent(self, result)
        hooks.beforeSummaryReport(reportEvent)
        if hasattr(result, 'separator2'):
            self.message(result.separator2, (0, 1, 2))
            self.message('\n')
        run = result.testsRun
        msg = ("Ran %d test%s in %.3fs\n\n" %
                            (run, run != 1 and "s" or "", timeTaken))
        self.message(msg, (0, 1, 2))
        
        infos = []
        extraInfos = []
        if result.wasSuccessful():
            self.message("OK", (0, 1, 2))
        else:
            self.message("FAILED", (0, 1, 2))

        if not hasattr(result, 'reportCategories'):
            expectedFails = unexpectedSuccesses = skipped = 0
            try:
                results = map(len, (result.expectedFailures,
                                    result.unexpectedSuccesses,
                                    result.skipped))
                expectedFails, unexpectedSuccesses, skipped = results
            except AttributeError:
                pass
            failed, errored = map(len, (result.failures, result.errors))
        else:
            failed = len(result.reportCategories.get('failed', []))
            errored = len(result.reportCategories.get('error', []))
            skipped = len(result.reportCategories.get('skipped', []))
            expectedFails = len(result.reportCategories.get('expectedFails', []))
            unexpectedSuccesses = len(result.reportCategories.get('unexpectedSuccesses', []))
            
            dontReport = set(['error', 'failed', 'skipped', 'passed',
                              'expectedFailures', 'unexpectedSuccess'])
            for flavour, results in result.reportCategories.items():
                if flavour in dontReport:
                    continue
                extraInfos.append("%s=%d" % (flavour, len(results)))

        if failed:
            infos.append("failures=%d" % failed)
        if errored:
            infos.append("errors=%d" % errored)
        if skipped:
            infos.append("skipped=%d" % skipped)
        if expectedFails:
            infos.append("expected failures=%d" % expectedFails)
        if unexpectedSuccesses:
            infos.append("unexpected successes=%d" % unexpectedSuccesses)
        infos.extend(extraInfos)
        if infos:
            self.message(" (%s)" % (", ".join(infos),), (0, 1, 2))
        self.message("\n")
        hooks.afterSummaryReport(reportEvent)
        return result
