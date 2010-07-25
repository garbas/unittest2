"""Unittest main program"""

import optparse
import os
import sys
import types

from unittest2 import loader, runner, __version__
try:
    from unittest2.signals import installHandler
except ImportError:
    installHandler = None

from unittest2.events import (
    loadPlugins, PluginsLoadedEvent,
    hooks
)

__unittest = True

FAILFAST     = "  -f, --failfast   Stop on first failure\n"
CATCHBREAK   = "  -c, --catch      Catch control-C and display results\n"
BUFFEROUTPUT = "  -b, --buffer     Buffer stdout and stderr during test runs\n"

USAGE_AS_MAIN = """\
Usage: %(progName)s [options] [tests]

Options:
  -h, --help       Show this message
  -v, --verbose    Verbose output
  -q, --quiet      Minimal output
%(failfast)s%(catchbreak)s%(buffer)s
Examples:
  %(progName)s test_module                       - run tests from test_module
  %(progName)s test_module.TestClass             - run tests from
                                                   test_module.TestClass
  %(progName)s test_module.TestClass.test_method - run specified test method

[tests] can be a list of any number of test modules, classes and test
methods.

Alternative Usage: %(progName)s discover [options]

Options:
  -v, --verbose    Verbose output
%(failfast)s%(catchbreak)s%(buffer)s  -s directory     Directory to start discovery ('.' default)
  -p pattern       Pattern to match test files ('test*.py' default)
  -t directory     Top level directory of project (default to
                   start directory)

For test discovery all test modules must be importable from the top
level directory of the project.
"""

USAGE_FROM_MODULE = """\
Usage: %(progName)s [options] [tests]

Options:
  -h, --help       Show this message
  -v, --verbose    Verbose output
  -q, --quiet      Minimal output
%(failfast)s%(catchbreak)s%(buffer)s
Examples:
  %(progName)s                               - run default set of tests
  %(progName)s MyTestSuite                   - run suite 'MyTestSuite'
  %(progName)s MyTestCase.testSomething      - run MyTestCase.testSomething
  %(progName)s MyTestCase                    - run all 'test*' test methods
                                               in MyTestCase
"""

DESCRIPTION = ('[tests] can be a list of any number of test modules, classes '
               'and test methods.')


class TestProgram(object):
    """A command-line program that runs a set of tests; this is primarily
       for making test modules conveniently executable.
    """
    USAGE = USAGE_FROM_MODULE
    
    # defaults for testing
    failfast = catchbreak = buffer = progName = None
    
    pluginsLoaded = False

    def __init__(self, module='__main__', defaultTest=None,
                 argv=None, testRunner=None,
                 testLoader=loader.defaultTestLoader, exit=True,
                 verbosity=1, failfast=None, catchbreak=None, buffer=None):
        if isinstance(module, basestring):
            self.module = __import__(module)
            for part in module.split('.')[1:]:
                self.module = getattr(self.module, part)
        else:
            self.module = module
        if argv is None:
            argv = sys.argv

        self.exit = exit
        self.verbosity = verbosity
        self.failfast = failfast
        self.catchbreak = catchbreak
        self.buffer = buffer
        self.defaultTest = defaultTest
        self.testRunner = testRunner
        self.testLoader = testLoader
        self.progName = os.path.basename(argv[0])
        
        if not TestProgram.pluginsLoaded:
            # only needed because we call several times during tests
            loadPlugins()
            TestProgram.pluginsLoaded = True
        
        self.parseArgs(argv)
        self.runTests()

    def usageExit(self, msg=None):
        if msg:
            print msg
        usage = {'progName': self.progName, 'catchbreak': '', 'failfast': '',
                 'buffer': ''}
        if self.failfast != False:
            usage['failfast'] = FAILFAST
        if self.catchbreak != False and installHandler is not None:
            usage['catchbreak'] = CATCHBREAK
        if self.buffer != False:
            usage['buffer'] = BUFFEROUTPUT
        print self.USAGE % usage
        sys.exit(2)

    def parseArgs(self, argv):
        if len(argv) > 1 and argv[1].lower() == 'discover':
            self._do_discovery(argv[2:])
            return
        
        if len(argv) == 1 and self.module is None and self.defaultTest is None:
            # launched with no args from script
            self._do_discovery([])
            return

        options, args = self._parseArgs(argv[1:], forDiscovery=False)
        
        if len(args) == 0 and self.defaultTest is None:
            # createTests will load tests from self.module
            self.testNames = None
        elif len(args) > 0:
            self.testNames = args
            if __name__ == '__main__':
                # to support python -m unittest ...
                self.module = None
        else:
            self.testNames = (self.defaultTest,)
        
        self.createTests()

    def createTests(self):
        if self.testNames is None:
            self.test = self.testLoader.loadTestsFromModule(self.module)
        else:
            self.test = self.testLoader.loadTestsFromNames(self.testNames,
                                                            self.module)

    def _parseArgs(self, argv, forDiscovery):
        parser = optparse.OptionParser(version='unittest2 %s' % __version__)
        if forDiscovery:
            parser.usage = '%prog [options] [...]'
        else:
            parser.description = DESCRIPTION
            parser.usage = '%prog [options] [tests]'
        parser.prog = self.progName
        parser.add_option('-v', '--verbose', dest='verbose', default=False,
                          help='Verbose output', action='store_true')
        parser.add_option('-q', '--quiet', dest='quiet', default=False,
                          help='Quiet output', action='store_true')
        if self.failfast != False:
            parser.add_option('-f', '--failfast', dest='failfast', default=False,
                              help='Stop on first fail or error', 
                              action='store_true')
        if self.catchbreak != False and installHandler is not None:
            parser.add_option('-c', '--catch', dest='catchbreak', default=False,
                              help='Catch ctrl-C and display results so far', 
                              action='store_true')
        if self.buffer != False:
            parser.add_option('-b', '--buffer', dest='buffer', default=False,
                              help='Buffer stdout and stderr during tests', 
                              action='store_true')

        if forDiscovery:
            parser.add_option('-s', '--start-directory', dest='start', default='.',
                              help="Directory to start discovery ('.' default)")
            parser.add_option('-p', '--pattern', dest='pattern', default=None,
                              help="Pattern to match tests ('test*.py' default)")
            parser.add_option('-t', '--top-level-directory', dest='top', default=None,
                              help='Top level directory of project (defaults to start directory)')

        list_options = []
        extra_options = []
        if forDiscovery:
            extra_options = _discoveryOptions
        for opt, longopt, help_text, callback in _options + extra_options:
            opts = []
            if opt is not None:
                opts.append('-' + opt)
            if longopt is not None:
                opts.append('--' + longopt)
            kwargs = dict(
                action='callback',
                help=help_text,
            )
            if isinstance(callback, list):
                kwargs['action'] = 'append'
                kwargs['dest'] = longopt
                list_options.append((longopt, callback))
            else:
                kwargs['callback'] = callback
            option = optparse.make_option(*opts, **kwargs)
            parser.add_option(option)
            
        options, args = parser.parse_args(argv)
        for attr, _list in list_options:
            values = getattr(options, attr) or []
            _list.extend(values)

        # only set options from the parsing here
        # if they weren't set explicitly in the constructor
        if self.failfast is None:
            self.failfast = options.failfast
        if self.catchbreak is None and installHandler is not None:
            self.catchbreak = options.catchbreak
        if self.buffer is None:
            self.buffer = options.buffer
        
        if options.verbose:
            self.verbosity = 2
        if options.quiet:
            self.verbosity = 0
        
        hooks.pluginsLoaded(PluginsLoadedEvent())
        return options, args
        
    def _do_discovery(self, argv, Loader=loader.TestLoader):
        # handle command line args for test discovery
        self.progName = '%s discover' % self.progName
        options, args = self._parseArgs(argv, forDiscovery=True)
        
        if len(args) > 3:
            self.usageExit()
        
        for name, value in zip(('start', 'pattern', 'top'), args):
            setattr(options, name, value)

        start_dir = options.start
        pattern = options.pattern
        top_level_dir = options.top

        loader = Loader()
        self.test = loader.discover(start_dir, pattern, top_level_dir)

    def runTests(self):
        if self.catchbreak:
            installHandler()
        if self.testRunner is None:
            self.testRunner = runner.TextTestRunner
        if isinstance(self.testRunner, (type, types.ClassType)):
            try:
                testRunner = self.testRunner(verbosity=self.verbosity,
                                             failfast=self.failfast,
                                             buffer=self.buffer)
            except TypeError:
                # didn't accept the verbosity, buffer or failfast arguments
                testRunner = self.testRunner()
        else:
            # it is assumed to be a TestRunner instance
            testRunner = self.testRunner
        self.result = testRunner.run(self.test)
        if self.exit:
            sys.exit(not self.result.wasSuccessful())

    

def main_():
    TestProgram.USAGE = USAGE_AS_MAIN
    TestProgram(module=None)

_options = []
_discoveryOptions = []