import os

from ConfigParser import SafeConfigParser
from ConfigParser import Error as ConfigParserError

CFG_NAME = 'unittest.cfg'

DEFAULT = object()
RETURN_DEFAULT = object()
TRUE = set((True, '1', 'true', 'on', 'yes'))
FALSE = set((False, '0', 'false', 'off', 'no', ''))

_config = None

__all__ = (
    'loadConfig',
    'getConfig',
)

def getConfig(section=None):
    # warning! mutable
    if section is None:
        return _config
    return _config.get(section, Section(section))


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


def loadConfig(noUserConfig=False, configLocations=None):
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
                    

    plugins = set(sum([plugin for plugin, parser in configs], []))
    parsers = [parser for plugin, parser in configs]
    _config = combineConfigs(parsers)
    return plugins


class Section(dict):
    def __new__(cls, name, items=()):
        return dict.__new__(cls, items)

    def __init__(self, name, items=()):
        self.name = name

    def __repr__(self):
        return 'Section(%r, %r)' % (self.name, self.items())

    def _get_value(self, item, default, allowEmpty, lower=False):
        try:
            value = self[item]
        except KeyError:
            if default is not DEFAULT:
                return RETURN_DEFAULT
            raise
        if isinstance(value, basestring):
            value = value.strip()
            if lower:
                value = value.lower()

        if not allowEmpty and value == '':
            if default is not DEFAULT:
                return RETURN_DEFAULT
            raise ValueError(item)
        return value

    def as_bool(self, item, default=DEFAULT):
        value = self._get_value(item, default, allowEmpty=True, lower=True)
        if value is RETURN_DEFAULT:
            return default
        return self._as_bool(value, item)

    def as_tri(self, item, default=DEFAULT):
        value = self._get_value(item, default, allowEmpty=True)
        if value is RETURN_DEFAULT:
            return default
        if not value:
            return None
        return self._as_bool(value, item)

    def _as_bool(self, value, item):
        if value in TRUE:
            return True
        if value in FALSE:
            return False
        raise ConfigParserError('Config file value %s : %s : %s not recognised'
                                ' as a boolean' % (self.name, item, value))

    def as_int(self, item, default=DEFAULT):
        value = self._get_value(item, default, allowEmpty=False)
        if value is RETURN_DEFAULT:
            return default
        return int(value)

    def as_float(self, item, default=DEFAULT):
        value = self._get_value(item, default, allowEmpty=False)
        if value is DEFAULT:
            return default
        return float(value)

    def as_str(self, item, default=DEFAULT):
        value = self._get_value(item, default, allowEmpty=True)
        if value is DEFAULT:
            return default
        return value

    def as_list(self, item, default=DEFAULT):
        value = self._get_value(item, default, allowEmpty=True)
        if value is DEFAULT:
            return default
        return [line.strip() for line in value.splitlines()
                 if line.strip() and not line.strip().startswith('#')]

