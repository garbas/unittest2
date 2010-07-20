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



CFG_NAME = 'unittest.cfg'
def loadPlugins(projectDir):
    cfgPath = os.path.join(projectDir, CFG_NAME)
    plugins = loadPluginsConfigFile(cfgPath)
    for plugin in plugins:
        __import__(plugin)

def loadPluginsConfigFile(path):
    parser = SafeConfigParser()
    parser.read(path)
    plugins = []
    try:
        return [line for line in 
                 parser.get('unittest', 'plugins').splitlines()
                 if line.strip() and not line.strip().startswith('#')]
    except ConfigParserError:
        return plugins

def addOption(callback, opt, longOpt=None, help=None):
    # delayed import to avoid circular imports
    from unittest2.main import _options
    
    if opt and opt.lower() == opt:
        raise ValueError('Lowercase short options are reserved: %s' % opt)
    wrappedCallback = lambda *_: callback()
    _options.append((opt, longOpt, help, wrappedCallback))