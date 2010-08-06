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

from unittest2.config import getConfig
from unittest2.events import (
    loadPlugins, PluginsLoadedEvent,
    hooks, HandleFileEvent
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

DESCRIPTION = (
    '[tests] can be a list of any number of test modules, classes '
    'and test methods. The discover subcommand starts test discovery.'
)

# AttributeError only needed for Python 2.4
_OPT_ERRS = (optparse.BadOptionError, optparse.OptionValueError, AttributeError)

class _ImperviousOptionParser(optparse.OptionParser):
    def error(self, msg):
        pass
    def exit(self, status=0, msg=None):
        pass
    
    print_usage = print_version = print_help = lambda self, file=None: None

    def _process_short_opts(self, rargs, values):
        try:
            optparse.OptionParser._process_short_opts(self, rargs, values)
        except _OPT_ERRS:
            pass

    def _process_long_opt(self, rargs, values):
        try:
            optparse.OptionParser._process_long_opt(self, rargs, values)
        except _OPT_ERRS:
            pass


class _Callback(object):
    def __init__(self, callback):
        self.callback = callback
    def __call__(self, *_):
        self.callback()


class TestProgram(object):
    """A command-line program that runs a set of tests; this is primarily
       for making test modules conveniently executable.
    """
    USAGE = USAGE_FROM_MODULE
    
    # defaults for testing
    failfast = catchbreak = buffer = progName = module = defaultTest = None
    pluginsLoaded = verbosity = extraConfig = None

    def __init__(self, module='__main__', defaultTest=None,
                 argv=None, testRunner=None,
                 testLoader=loader.defaultTestLoader, exit=True,
                 verbosity=None, failfast=None, catchbreak=None, buffer=None,
                 config=None):
        if isinstance(module, basestring):
            __import__(module)
            self.module = sys.modules[module]
        else:
            self.module = module

        self.extraConfig = config
        if isinstance(verbosity, basestring):
            # allow string verbosities not in the dictionary
            # for backwards compatibility
            verbosity = runner.VERBOSITIES.get(verbosity.lower(), verbosity)

        if argv is None:
            argv = sys.argv

        self.exit = exit
        self.verbosity = verbosity
        self.failfast = failfast
        self.catchbreak = catchbreak
        self.buffer = buffer
        self.defaultTest = defaultTest
        self.testRunner = testRunner
        
        if isinstance(testLoader, type):
            testLoader = testLoader()
        self.testLoader = testLoader
        self.progName = os.path.basename(argv[0])

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
        forDiscovery = False
        if len(argv) > 1 and argv[1].lower() == 'discover':
            # handle command line args for test discovery
            self.progName = '%s discover' % self.progName
            argv = argv[1:]
            forDiscovery = True

        options, args = self._parseArgs(argv[1:], forDiscovery=forDiscovery)
        if (not forDiscovery and not args and self.module is None and 
            self.defaultTest is None):
            # launched with no args from script
            options.start = '.'
            options.top = options.pattern = None
            forDiscovery =True

        if forDiscovery:
            self._do_discovery(options, args)
            return
        
        if len(args) == 0 and self.defaultTest is None:
            # createTests will load tests from self.module
            self.testNames = None
        elif len(args) > 0:
            self.testNames = args
        else:
            self.testNames = (self.defaultTest,)
        
        self.createTests()

    def createTests(self):
        if self.testNames is None:
            self.test = self.testLoader.loadTestsFromModule(self.module)
        else:
            tests = []
            top_level = os.getcwd()
            loader = self.testLoader
            pattern = None
            # we could store the original and then restore after monkeypatch
            # probably not really an issue as this test runner is not intended
            # to be reused
            loader._top_level_dir = top_level
            
            for name in self.testNames:
                try:
                    test = self.testLoader.loadTestsFromName(name, self.module)
                except ImportError, e:
                    if not os.path.isfile(name):
                        raise
                    else:
                        path = os.path.split(name)[1]
                        event = HandleFileEvent(loader, path, name, pattern,
                                                top_level)
                        result = hooks.handleFile(event)
                        tests.extend(event.extraTests)
                        if event.handled:
                            tests.extend(result)
                            continue
                        
                        try:
                            name = loader._get_name_from_path(name)
                            test = self.testLoader.loadTestsFromName(name,
                                                                     self.module)
                        except (ImportError, AssertionError):
                            # better error message here perhaps?
                            raise e
                        tests.append(test)
                else:
                    tests.append(test)
                        
            self.test = self.testLoader.suiteClass(tests)

    def _getConfigOptions(self, argv):
        # an initial pass over command line options to load config files
        # and plugins
        parser = _ImperviousOptionParser()
        parser.add_option('--config', dest='configLocations', action='append')
        parser.add_option('--no-user-config', dest='noUserConfig', default=False,
                          action='store_true')
        parser.add_option('--no-plugins', dest='pluginsDisabled', default=False,
                          action='store_true')

        if TestProgram.pluginsLoaded:
            # only needed because we call several times during tests
            return False

        # we catch any optparse errors here as they will be
        # reraised on the second pass through
        try:
            options, _ = parser.parse_args(argv)
        except optparse.OptionError:
            pluginsDisabled = False
            noUserConfig = False
            configLocations = []
        else:
            pluginsDisabled = options.pluginsDisabled
            noUserConfig = options.noUserConfig
            configLocations = options.configLocations

        loadPlugins(pluginsDisabled, noUserConfig, configLocations,
                    self.extraConfig)
        TestProgram.pluginsLoaded = True
        return pluginsDisabled


    def _parseArgs(self, argv, forDiscovery):
        pluginsDisabled = self._getConfigOptions(argv)
        
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
        
        parser.add_option('--config', dest='configLocations', action='append',
                          help='Specify local config file location')
        parser.add_option('--no-user-config', dest='noUserConfig', default=False,
                          action='store_true',
                          help="Don't use user config file")
        parser.add_option('--no-plugins', dest='pluginsDisabled', default=False,
                          action='store_true', help="Disable all plugins")
        
        if self.failfast != False:
            parser.add_option('-f', '--failfast', dest='failfast', default=None,
                              help='Stop on first fail or error', 
                              action='store_true')
        if self.catchbreak != False and installHandler is not None:
            parser.add_option('-c', '--catch', dest='catchbreak', default=None,
                              help='Catch ctrl-C and display results so far', 
                              action='store_true')
        if self.buffer != False:
            parser.add_option('-b', '--buffer', dest='buffer', default=None,
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

        if not pluginsDisabled:
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
                    kwargs['callback'] = _Callback(callback)
                option = optparse.make_option(*opts, **kwargs)
                parser.add_option(option)

        options, args = parser.parse_args(argv)

        for attr, _list in list_options:
            values = getattr(options, attr) or []
            _list.extend(values)

        config = getConfig('unittest')
        if self.verbosity is None:
            try:
                self.verbosity = config.as_int('verbosity', 1)
            except ValueError:
                if ('verbosity' in config and 
                    config['verbosity'].lower() in runner.VERBOSITIES):
                    self.verbosity = runner.VERBOSITIES[config['verbosity']]
                else:
                    raise

        config['discover'] = forDiscovery

        if self.buffer is not None:
            options.buffer = self.buffer
        if self.failfast is not None:
            options.failfast = self.failfast
        if installHandler is None:
            options.catchbreak = False
        elif self.catchbreak is not None:
            options.catchbreak = self.catchbreak

        if options.buffer is None:
            options.buffer = config.as_bool('buffer', default=False)
        if options.failfast is None:
            options.failfast = config.as_bool('failfast', default=False)
        if options.catchbreak is None:
            options.catchbreak = config.as_bool('catch', default=False)

        self.failfast = options.failfast
        self.buffer = options.buffer
        self.catchbreak = options.catchbreak

        if options.verbose:
            self.verbosity = 2
        if options.quiet:
            self.verbosity = 0
        if options.quiet and options.verbose:
            # could raise an exception here I suppose
            self.verbosity = 1

        config['verbosity'] = self.verbosity
        config['buffer'] = self.buffer
        config['catch'] = self.catchbreak
        config['failfast'] = self.failfast

        hooks.pluginsLoaded(PluginsLoadedEvent())
        return options, args

    def _do_discovery(self, options, args):
        if len(args) > 3:
            self.usageExit()
        
        for name, value in zip(('start', 'pattern', 'top'), args):
            setattr(options, name, value)

        start_dir = options.start
        pattern = options.pattern
        top_level_dir = options.top

        loader = self.testLoader
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