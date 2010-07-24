import os
import sys

from ConfigParser import SafeConfigParser
from ConfigParser import Error as ConfigParserError

# TODO: messaging API that respects verbosity
# TestFailEvent in setUpClass and setUpModule etc


__all__ = (
    # events
    'PluginsLoadedEvent',
    'HandleFileEvent',
    'MatchPathEvent',
    'GetTestCaseNamesEvent',
    'LoadFromNamesEvent',
    'LoadFromNameEvent',
    'LoadFromModuleEvent',
    'LoadFromTestCaseEvent',
    'StartTestRunEvent',
    'StopTestRunEvent',
    'StartTestEvent',
    'StopTestEvent',
    'TestFailEvent',
    # for plugins
    'hooks',
    'addOption',
    'getConfig',
    'Plugin',
    'pluginInstances',
    # API for test frameworks
    'loadedPlugins',
    'loadPlugins',
    'loadPlugin',
    'loadConfig',
)


_config = None
loadedPlugins = []
CFG_NAME = 'unittest.cfg'
pluginInstances = set()

class _Event(object):
    def __init__(self):
        self.handled = False


class HandleFileEvent(_Event):
    def __init__(self, loader, name, path, pattern,
                    top_level_directory):
        _Event.__init__(self)
        self.extraTests = []
        self.path = path
        self.loader = loader
        self.name = name
        self.pattern = pattern
        self.top_level_directory = top_level_directory

class MatchPathEvent(_Event):
    def __init__(self, name, path, pattern):
        _Event.__init__(self)
        self.path = path
        self.name = name
        self.pattern = pattern

class LoadFromModuleEvent(_Event):
    def __init__(self, loader, module):
        _Event.__init__(self)
        self.loader = loader
        self.module = module
        self.extraTests = []

class LoadFromTestCaseEvent(_Event):
    def __init__(self, loader, testCase):
        _Event.__init__(self)
        self.loader = loader
        self.testCase = testCase
        self.extraTests = []

class LoadFromNameEvent(_Event):
    def __init__(self, loader, name, module):
        _Event.__init__(self)
        self.loader = loader
        self.name = name
        self.module = module
        self.extraTests = []

class LoadFromNamesEvent(_Event):
    def __init__(self, loader, names, module):
        _Event.__init__(self)
        self.loader = loader
        self.names = names
        self.module = module
        self.extraTests = []

class GetTestCaseNamesEvent(_Event):
    def __init__(self, loader, testCase):
        _Event.__init__(self)
        self.loader = loader
        self.testCase = testCase
        self.testMethodPrefix = None
        self.extraNames = []
        self.excludedNames = []

class TestFailEvent(_Event):
    def __init__(self, test, result, exc_info, when):
        _Event.__init__(self)
        self.test = test
        self.result = result
        self.exc_info = exc_info
        
        # 'setUp', 'call', 'tearDown', 'cleanUp'
        self.when = when
        

class StartTestRunEvent(_Event):
    def __init__(self, runner, result, startTime):
        _Event.__init__(self)
        self.runner = runner
        self.result = result
        self.startTime = startTime

class StopTestRunEvent(_Event):
    def __init__(self, runner, result, stopTime, timeTaken):
        _Event.__init__(self)
        self.runner = runner
        self.result = result
        self.stopTime = stopTime
        self.timeTaken = timeTaken

class StartTestEvent(_Event):
    def __init__(self, test, result, startTime):
        _Event.__init__(self)
        self.test = test
        self.result = result
        self.startTime = startTime

class StopTestEvent(_Event):
    def __init__(self, test, result, stopTime, timeTaken, 
                    outcome, exc_info=None, stage=None):
        self.test = test
        self.result = result
        self.stopTime = stopTime
        self.timeTaken = timeTaken
        self.exc_info = exc_info
        
        # class, setUp, call, tearDown, cleanUp
        # or None for a pass
        self.stage = stage
        self.outcome = outcome
        
        self.passed = False
        self.failed = False
        self.error = False
        self.skipped = False
        self.unexpectedSuccess = False
        self.expectedFailure = False
        if outcome == 'passed':
            self.passed = True
        elif outcome == 'failed':
            self.failed = True
        elif outcome == 'error':
            self.error = True
        elif outcome == 'skipped':
            self.skipped = True
        elif outcome == 'unexpectedSuccess':
            self.unexpectedSuccess = True
        elif outcome == 'expectedFailure':
            self.expectedFailure = True

class _EventHook(object):
    def __init__(self):
        # can't use a deque because it has no remove in
        # python 2.4
        self._handlers = []
    
    def __call__(self, event):
        for handler in self._handlers:
            result = handler(event)
            if event.handled:
                return result
    
    def __iadd__(self, handler):
        self._handlers.insert(0, handler)
        return self
        
    def __isub__(self, handler):
        self._handlers.remove(handler)
        return self

class PluginsLoadedEvent(_Event):
    loadedPlugins = loadedPlugins


class hooks(object):
    pluginsLoaded = _EventHook()
    
    # discovery only
    handleFile = _EventHook()
    matchPath = _EventHook()
    
    loadTestsFromModule = _EventHook()
    loadTestsFromTestCase = _EventHook()
    loadTestsFromName = _EventHook()
    loadTestsFromNames = _EventHook()
    getTestCaseNames = _EventHook()
    onTestFail = _EventHook()
    startTestRun = _EventHook()
    stopTestRun = _EventHook()
    
    startTest = _EventHook()
    stopTest = _EventHook()


class Register(type):
    def __new__(meta, name, bases, contents):
        autoCreate = contents.get('autoCreate')
        if autoCreate is not None:
            del contents['autoCreate']
        else:
            autoCreate = True
        cls = type.__new__(meta, name, bases, contents)
        
        if autoCreate:
            cls()
        return cls
        

class Plugin(object):
    __metaclass__ = Register
    
    def __new__(cls, *args, **kw):
        instance = object.__new__(cls)
        pluginInstances.add(instance)
        if cls.instance is None:
            cls.instance = instance
        return instance
    
    def register(self):
        hook_points = set(dir(hooks))
        for entry in dir(self):
            if entry.startswith('_'):
                continue
            if entry in hook_points:
                point = getattr(hooks, entry)
                point += getattr(self, entry)
    
    def unregister(self):
        cls = self.__class__
        pluginInstances.remove(self)
        hook_points = set(dir(hooks))
        for entry in dir(self):
            if entry.startswith('_'):
                continue
            if entry in hook_points:
                point = getattr(hooks, entry)
                point -= getattr(self, entry)
        if cls.instance is self:
            cls.instance = None
    
    instance = None
    autoCreate = False

    
def loadPlugins():
    allPlugins = loadConfig()
    for plugin in allPlugins:
        loadPlugin(plugin)

def loadPlugin(plugin):
    __import__(plugin)
    mod = sys.modules[plugin]
    initialise = getattr(mod, 'initialise', None)
    if initialise is not None:
        initialise()
    loadedPlugins.append(plugin)

def loadConfig(name=CFG_NAME, localDir=None):
    global _config
    if localDir is None:
        # should use project top level directory - but we
        # don't know it when this is called
        localDir = os.getcwd()
    
    cfgPath = os.path.join(os.path.expanduser('~'), name)
    globalPlugins, globalParser = loadPluginsConfigFile(cfgPath)
    cfgPath = os.path.join(localDir, name)
    localPlugins, localParser = loadPluginsConfigFile(cfgPath)

    _config = combineConfigs(globalParser, localParser)
    return set(globalPlugins + localPlugins)

DEFAULT = object()
TRUE = set(('1', 'true', 'on', 'yes'))
FALSE = set(('0', 'false', 'off', 'no', ''))

class Section(dict):
    def __new__(cls, name, items=()):
        return dict.__new__(cls, items)

    def __init__(self, name, items=()):
        self.name = name

    def as_bool(self, item, default=DEFAULT):
        try:
            value = self[item].lower().strip()
        except KeyError:
            if default is not DEFAULT:
                return default
            raise
        if value in TRUE:
            return True
        if value in FALSE:
            return False
        raise ConfigParserError('Config file value %s:%s:%s not recognised'
                                 ' as a boolean' % (self.name, item, value))

    def __repr__(self):
        return 'Section(%r, %r)' % (self.name, self.items())
    
    def as_int(self, item, default=DEFAULT):
        try:
            return int(self[item].strip())
        except KeyError:
            if default is not DEFAULT:
                return default
            raise
    
    def as_str(self, item, default=DEFAULT):
        try:
            # to strip or not to strip here?
            return self[item]
        except KeyError:
            if default is not DEFAULT:
                return default
            raise
    
    def as_float(self, item, default=DEFAULT):
        try:
            return float(self[item].strip())
        except KeyError:
            if default is not DEFAULT:
                return default
            raise
    
    def as_list(self, item, default=DEFAULT):
        try:
            entry = self[item]
        except KeyError:
            if default is not DEFAULT:
                return default
            raise
        return [line.strip() for line in entry.splitlines()
                 if line.strip() and not line.strip().startswith('#')]


def combineConfigs(globalParser, localParser):
    options = {}
    for section in globalParser.sections():
        options[section] = Section(section, globalParser.items(section))
    for section in localParser.sections():
        items = dict(localParser.items(section))
        options.setdefault(section, Section(section)).update(items)
    return options


def loadPluginsConfigFile(path):
    parser = SafeConfigParser()
    parser.read(path)
    plugins = []
    try:
        plugins = [line for line in 
                   parser.get('unittest', 'plugins').splitlines()
                   if line.strip() and not line.strip().startswith('#')]
        return plugins, parser
    except ConfigParserError:
        return plugins, parser

def addOption(callback, opt=None, longOpt=None, help=None):
    # delayed import to avoid circular imports
    from unittest2.main import _options
    _addOption(callback, opt, longOpt, help, optionList=_options)

def _addOption(callback, opt, longOpt, help, optionList):
    if opt and opt.lower() == opt:
        raise ValueError('Lowercase short options are reserved: %s' % opt)
    wrappedCallback = lambda *_: callback()
    if isinstance(callback, list):
        wrappedCallback = callback
    optionList.append((opt, longOpt, help, wrappedCallback))

def addDiscoveryOption(callback, opt=None, longOpt=None, help=None):
    # delayed import to avoid circular imports
    from unittest2.main import _discoveryOptions
    _addOption(callback, opt, longOpt, help, optionList=_discoveryOptions)
    
    
def getConfig(section=None):
    # warning! mutable
    if section is None:
        return _config
    return _config.get(section, Section(section))
