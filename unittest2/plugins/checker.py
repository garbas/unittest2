"""
Based on pytest-codecheckers:
    http://pypi.python.org/pypi/pytest-codecheckers/

By: Ronny Pfannschmidt
"""
from unittest2 import FunctionTestCase
from unittest2.events import Plugin
from unittest2.util import getSource

import sys

try:
    from pyflakes.scripts.pyflakes import check as pyflakes_check
except ImportError:
    pyflakes_check = None

try:
    import pep8
except ImportError:
    pep8 = None

# needs config options for independently controlling pep8 and pyflakes
# plus configuring which PEP8 warnings are enabled


help_text = 'Check all Python files with pep8 and pyflakes'

class Checker(Plugin):
    
    configSection = 'checker'
    commandLineSwitch = (None, 'checker', help_text)
    
    def pluginsLoaded(self, event):
        if not pep8 and not pyflakes_check:
            raise AssertionError('checker plugin requires pep8 or pyflakes')
        if pep8:
            pep8.process_options(['pep8',
                PEP8_IGNORE_LIST,
                '--show-source',
                '--repeat',
                'dummy file',
                ])

    def handleFile(self, event):
        path = event.path
        loader = event.loader
        if not path.lower().endswith('.py'):
            return
        
        suite = getSuite(path, loader)
        event.extraTests.append(suite)


class CheckerTestCase(FunctionTestCase):
    traceback = None

    def __init__(self, path, func):
        self.path = path
        FunctionTestCase.__init__(self, func)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.path)
    
    def id(self):
        return repr(self)

    __str__ = __repr__

    def formatTraceback(self, err):
        exctype, value, tb = err
        if not exctype == self.failureException or self.traceback is None:
            return FunctionTestCase.formatTraceback(self, err)
        return self.traceback


class Pep8CheckerTestCase(CheckerTestCase):
    def __init__(self, path):
        func = lambda: check_file_pep8(path, self)
        CheckerTestCase.__init__(self, path, func)

class PyFlakesCheckerTestCase(CheckerTestCase):
    def __init__(self, path):
        func = lambda: check_file_pyflakes(path, self)
        CheckerTestCase.__init__(self, path, func)


class Stdout(object):
    def __init__(self):
        self.data = []
    def write(self, data):
        self.data.append(data)
    def writeln(self, data):
        self.data.append(data)
        self.data.append('\n')

def captured(func):
    original = sys.stdout
    sys.stdout = Stdout()
    try:
        result = func()
    finally:
        data = sys.stdout.data
        sys.stdout = original
    return ''.join(data), result


if pep8:
    Base = pep8.Checker
else:
    Base = object

class Pep8Checker(Base):
    ignored_errors = 0
    def report_error(self, line_number, offset, text, check):
        #XXX: pep8 is a retarded module!
        if pep8.ignore_code(text[:4]):
            self.ignored_errors += 1
        pep8.Checker.report_error(self, line_number, offset, text, check)

# ignore list taken from moin
# should be a config option
PEP8_IGNORE_LIST = (
    '--ignore=E202,E221,E222,E241,E301,E302,E401,E501,E701,W391,W601,W602'
)

    
def check_file_pep8(path, test):
    def checkFile():
        checker = Pep8Checker(path)
        #XXX: bails out on death
        error_count = checker.check_all()
        ignored = checker.ignored_errors
        return max(error_count - ignored, 0)
    
    output, result = captured(checkFile)
    if result:
        msg = 'pep8 reported %s errors.\n' % (result,)
        test.traceback = '\n'.join([msg, output])
        raise test.failureException(msg)

def check_file_pyflakes(path, test):
    def checkFile():
        handle = open(path)
        try:
            return pyflakes_check(handle.read(), path)
        finally:
            handle.close()
        
    output, result = captured(checkFile)
    if result:
        msg = 'pyflakes reported %s errors.\n' % (result,)
        test.traceback = '\n'.join([msg, output])
        raise test.failureException(msg)


def getSuite(path, loader):
    tests = []
    if pep8:
        test = Pep8CheckerTestCase(path)
        tests.append(test)
    if pyflakes_check:
        test = PyFlakesCheckerTestCase(path)
        tests.append(test)
    
    return loader.suiteClass(tests)



