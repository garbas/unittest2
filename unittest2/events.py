import sys

from unittest2.config import loadConfig, getConfig


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
    'Plugin',
    'pluginInstances',
    # API for test frameworks
    'loadedPlugins',
    'loadPlugins',
    'loadPlugin',
)


loadedPlugins = []
pluginInstances = set()


class _Event(object):
    _message = None
    def __init__(self):
        self.handled = False
    
    def message(self, msg, verbosity=(1, 2)):
        if self._message is None:
            from unittest2.runner import message
            _Event._message = staticmethod(message)
        self._message(msg, verbosity)

class MessageEvent(_Event):
    def __init__(self, runner, stream, message, verbosity):
        _Event.__init__(self)
        self.runner = runner
        self.message = message
        self.verbosity = verbosity
        self.stream = stream
    
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
    def __init__(self, test, result, exc_info, when, internal):
        _Event.__init__(self)
        self.test = test
        self.result = result
        self.exc_info = exc_info
        self.internal = internal
        
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

class AfterSetUpEvent(_Event):
    def __init__(self, test, result, exc_info, time):
        _Event.__init__(self)
        self.test = test
        self.result = result
        self.exc_info = exc_info
        self.time = time

class BeforeTearDownEvent(_Event):
    def __init__(self, test, result, success, time):
        _Event.__init__(self)
        self.test = test
        self.result = result
        self.success = success
        self.time = time

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
    handleFile = _EventHook()
    
    # discovery only
    matchPath = _EventHook()

    loadTestsFromModule = _EventHook()
    loadTestsFromTestCase = _EventHook()
    loadTestsFromName = _EventHook()
    loadTestsFromNames = _EventHook()
    getTestCaseNames = _EventHook()

    runnerCreated = _EventHook()

    startTestRun = _EventHook()
    startTest = _EventHook()
    afterSetUp = _EventHook()
    onTestFail = _EventHook()
    beforeTearDown = _EventHook()
    stopTest = _EventHook()
    stopTestRun = _EventHook()
    message = _EventHook()


class Register(type):
    autoRegister = True
    
    def __new__(meta, name, bases, contents):
        autoCreate = contents.get('autoCreate')
        if autoCreate is not None:
            del contents['autoCreate']
        else:
            autoCreate = True
        cls = type.__new__(meta, name, bases, contents)
        
        if meta.autoRegister and autoCreate:
            cls()
        return cls


class Plugin(object):
    __metaclass__ = Register

    config = None
    configSection = None
    commandLineSwitch = None
    instance = None
    _registered = False
    autoCreate = False

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
        try:
            pluginInstances.remove(self)
        except KeyError:
            pass

        hook_points = set(dir(hooks))
        for entry in dir(self):
            if entry.startswith('_'):
                continue
            if entry in hook_points:
                point = getattr(hooks, entry)
                try:
                    point -= getattr(self, entry)
                except ValueError:
                    # event has already been unhooked
                    pass
        if cls.instance is self:
            cls.instance = None


def loadPlugins(pluginsDisabled=False, noUserConfig=False, 
                configLocations=None):
    allPlugins = loadConfig(noUserConfig, configLocations)
    
    if not pluginsDisabled:
        for plugin in set(allPlugins):
            loadPlugin(plugin)
    
    # switch off autoregistration after plugins are loaded
    Register.autoRegister = False
    


def loadPlugin(plugin):
    __import__(plugin)
    sys.modules[plugin]
    loadedPlugins.append(plugin)


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

