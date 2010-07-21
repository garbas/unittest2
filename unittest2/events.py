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


class events(object):
    handleFile = _EventHook()
    matchPath = _EventHook()



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


class UsefulDict(dict):
    def as_bool(self, item):
        value = self[item].lower().strip()
        return value in ('1', 'true', 'on', 'yes')
    
    def as_int(self, item):
        return int(self[item])
    
    def as_float(self, item):
        return float(self[item])

def combineConfigs(globalParser, localParser):
    options = UsefulDict()
    for section in globalParser.sections():
        options[section] = UsefulDict(globalParser.items(section))
    for section in localParser.sections():
        items = UsefulDict(localParser.items(section))
        options.setdefault(section, UsefulDict()).update(items)
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