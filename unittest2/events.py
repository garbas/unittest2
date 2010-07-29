import os
import sys

from ConfigParser import SafeConfigParser
from ConfigParser import Error as ConfigParserError


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

DEFAULT = object()
TRUE = set(('1', 'true', 'on', 'yes'))
FALSE = set(('0', 'false', 'off', 'no', ''))


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
        
        # note: pattern may be None if not called during test discovery
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

class RunnerCreatedEvent(_Event):
    def __init__(self, runner):
        _Event.__init__(self)
        self.runner = runner

class TestFailEvent(_Event):
    def __init__(self, test, result, exc_info, when):
        _Event.__init__(self)
        self.test = test
        self.result = result
        self.exc_info = exc_info
        
        # 'setUp', 'call', 'tearDown', 'cleanUp'
        self.when = when
        

class StartTestRunEvent(_Event):
    def __init__(self, runner, suite, result, startTime):
        _Event.__init__(self)
        self.suite = suite
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
        _Event.__init__(self)
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
        self.skipReason = None
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
            self.skipReason = str(exc_info[1])
        elif outcome == 'unexpectedSuccess':
            self.unexpectedSuccess = True
        elif outcome == 'expectedFailure':
            self.expectedFailure = True

class PluginsLoadedEvent(_Event):
    loadedPlugins = loadedPlugins

_pluginsEnabled = True

class _EventHook(object):
    def __init__(self):
        # can't use a deque because it has no remove in
        # python 2.4
        self._handlers = []
    
    def __call__(self, event):
        if not _pluginsEnabled:
            return
        # list(...) needed because handlers can remove themselves inside this
        # loop - mutating self._handlers
        for handler in list(self._handlers):
            result = handler(event)
            if event.handled:
                return result
            continue
    
    def __iadd__(self, handler):
        self._handlers.insert(0, handler)
        return self
        
    def __isub__(self, handler):
        self._handlers.remove(handler)
        return self


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
    runnerCreated = _EventHook()


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

    config = None
    configSection = None
    commandLineSwitch = None
    instance = None
    _registered = False

    def __new__(cls, *args, **kw):
        instance = object.__new__(cls)
        pluginInstances.add(instance)
        if cls.instance is None:
            cls.instance = instance

        alwaysOn = False
        configSection = getattr(instance, 'configSection', None)
        commandLineSwitch = getattr(instance, 'commandLineSwitch', None)

        if configSection is not None:
            instance.config = getConfig(configSection)
            alwaysOn = instance.config.as_bool('always-on', default=False)

        if alwaysOn:
            instance.register()
        else:
            if commandLineSwitch is not None:
                opt, longOpt, help_text = commandLineSwitch
                addOption(instance.register, opt, longOpt, help_text)

        return instance
    
    def register(self):
        if self._registered:
            return
        
        self._registered = True
        hook_points = set(dir(hooks))
        for entry in dir(self):
            if entry.startswith('_'):
                continue
            if entry in hook_points:
                point = getattr(hooks, entry)
                point += getattr(self, entry)
    
    def unregister(self):
        self._registered = False
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


    
def loadPlugins(pluginsDisabled, noUserConfig, configLocations):
    allPlugins = loadConfig(noUserConfig, configLocations)
    
    if not pluginsDisabled:
        for plugin in allPlugins:
            loadPlugin(plugin)


def loadPlugin(plugin):
    __import__(plugin)
    sys.modules[plugin]
    loadedPlugins.append(plugin)


def loadConfig(noUserConfig, configLocations):
    global _config
    
    configs = []
    if not noUserConfig:
        cfgPath = os.path.join(os.path.expanduser('~'), CFG_NAME)
        userPlugins, userParser = loadPluginsConfigFile(cfgPath)
        configs.append((userPlugins, userParser))
    
    
    if not configLocations:
        cfgPath = os.path.join(os.getcwd(), CFG_NAME)
        localPlugins, localParser = loadPluginsConfigFile(cfgPath)
        configs.append((localPlugins, localParser))
    else:
        for entry in configLocations:
            path = entry
            if not os.path.isfile(path):
                path = os.path.join(path, CFG_NAME)
                if not os.path.isfile(path):
                    # exception type?
                    raise Exception('Config file location %r could not be found'
                                    % entry)
            
            plugins, parser = loadPluginsConfigFile(path)
            configs.append((plugins, parser))
                    

    plugins = set(sum([plugins for plugins, parser in configs], []))
    parsers = [parser for plugins, parser in configs]
    _config = combineConfigs(parsers)
    return plugins


def combineConfigs(parsers):
    options = {}
    for parser in parsers:
        for section in parser.sections():
            items = dict(parser.items(section))
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
