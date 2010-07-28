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
    
    def initialise(self):
        if not pep8 and not pyflakes_check:
            raise AssertionError('checker plugin requires pep8 or pyflakes')

    def handleFile(self, event):
        path = event.path
        loader = event.loader
        if not path.lower().endswith('.py'):
            return
        
        suite = getSuite(path, loader)
        event.extraTests.append(suite)


class CheckerTestCase(FunctionTestCase):
    def __init__(self, path, func):
        FunctionTestCase.__init__(self, func)
        self.path = path

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.path)
    
    def id(self):
        return repr(self)

    __str__ = __repr__

class Pep8CheckerTestCase(CheckerTestCase):
    pass

class PyFlakesCheckerTestCase(CheckerTestCase):
    pass

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


# ignore list taken from moin
# should be a config option
PEP8_IGNORE_LIST = (
    '--ignore=E202,E221,E222,E241,E301,E302,E401,E501,E701,W391,W601,W602'
)

    
def check_file_pep8(path):
    if not pep8:
        return
    
    class Pep8Checker(pep8.Checker):
        ignored_errors = 0
        def report_error(self, line_number, offset, text, check):
            #XXX: pep8 is a retarded module!
            if pep8.ignore_code(text[:4]):
                self.ignored_errors += 1
            pep8.Checker.report_error(self, line_number, offset, text, check)
    
    def checkFile():
        pep8.process_options(['pep8',
            PEP8_IGNORE_LIST,
            '--show-source',
            '--repeat',
            'dummy file',
            ])
        checker = Pep8Checker(path)
        #XXX: bails out on death
        error_count = checker.check_all()
        ignored = checker.ignored_errors
        return max(error_count - ignored, 0)
    
    output, result = captured(checkFile)
    if result:
        msg = 'pyflakes reported %s errors.\n\n%s' % (result, output)
        raise AssertionError(msg)

def check_file_pyflakes(path):
    def checkFile():
        handle = open(path)
        try:
            return pyflakes_check(handle.read(), path)
        finally:
            handle.close()
        
    output, result = captured(checkFile)
    if result:
        msg = 'pep8 reported %s errors.\n\n%s' % (result, output)
        raise AssertionError(msg)


def getSuite(path, loader):
    tests = []
    if pep8:
        tests.append(Pep8CheckerTestCase(path, lambda: check_file_pep8(path)))
    if pyflakes_check:
        tests.append(PyFlakesCheckerTestCase(path, lambda: check_file_pyflakes(path)))
    
    return loader.suiteClass(tests)



