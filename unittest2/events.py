import os

from ConfigParser import SafeConfigParser
from ConfigParser import Error as ConfigParserError


class _Event(object):
    def __init__(self):
        self.handled = False


class HandleFileEvent(_Event):
    def __init__(self, loader, name, path, pattern,
                    top_level_directory):
        _Event.__init__(self)
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

class OnTestFailEvent(_Event):
    def __init__(self, test, result, exc_info):
        _Event.__init__(self)
        self.test = test
        self.result = result
        self.exc_info = exc_info
    

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


class hooks(object):
    handleFile = _EventHook()
    matchPath = _EventHook()
    loadTestsFromModule = _EventHook()
    onTestFail = _EventHook()


_config = None
CFG_NAME = 'unittest.cfg'
def loadPlugins():
    global _config
    
    cfgPath = os.path.join(os.path.expanduser('~'), CFG_NAME)
    globalPlugins, globalParser = loadPluginsConfigFile(cfgPath)
    cfgPath = os.path.join(os.getcwd(), CFG_NAME)
    localPlugins, localParser = loadPluginsConfigFile(cfgPath)

    _config = combineConfigs(globalParser, localParser)

    for plugin in set(globalPlugins + localPlugins):
        __import__(plugin)


class Section(dict):
    def __new__(cls, name, items=()):
        return dict.__new__(cls, items)

    def __init__(self, name, items=()):
        self.name = name

    def as_bool(self, item):
        value = self[item].lower().strip()
        if value in ('1', 'true', 'on', 'yes'):
            return True
        if value in ('0', 'false', 'off', 'no'):
            return False
        raise ConfigParserError('Config file value %s:%s:%s not recognised'
                                 ' as a boolean' % (self.name, item, value))
    
    def as_int(self, item):
        return int(self[item].strip())
    
    def as_float(self, item):
        return float(self[item].strip())


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

def addOption(callback, opt, longOpt=None, help=None):
    # delayed import to avoid circular imports
    from unittest2.main import _options
    
    if opt and opt.lower() == opt:
        raise ValueError('Lowercase short options are reserved: %s' % opt)
    wrappedCallback = lambda *_: callback()
    _options.append((opt, longOpt, help, wrappedCallback))


def getConfig():
    # warning! mutable
    return _config
