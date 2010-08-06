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
    return _config.setdefault(section, Section(section))


def combineConfigs(parsers):
    options = {}
    for parser in parsers:
        for section in parser.sections():
            items = dict(parser.items(section))
            options.setdefault(section, Section(section)).update(items)

    return options

def _getList(parser, section, key):
    values = []
    try:
        values = [line for line in 
                   parser.get(section, key).splitlines()
                   if line.strip() and not line.strip().startswith('#')]
    except ConfigParserError:
        pass
    return values

def loadPluginsConfigFile(path):
    parser = SafeConfigParser()
    parser.read(path)
    plugins = _getList(parser, 'unittest', 'plugins')
    excludedPlugins = _getList(parser,'unittest', 'excluded-plugins')
    return parser, plugins, excludedPlugins


def loadConfig(noUserConfig=False, configLocations=None):
    global _config
    
    configs = []
    if not noUserConfig:
        cfgPath = os.path.join(os.path.expanduser('~'), CFG_NAME)
        userParser, userPlugins, userExcludedPlugins = loadPluginsConfigFile(cfgPath)
        configs.append((userPlugins, userParser, userExcludedPlugins))
    
    
    if configLocations is None:
        cfgPath = os.path.join(os.getcwd(), CFG_NAME)
        localParser, localPlugins, localExcludedPlugins = loadPluginsConfigFile(cfgPath)
        configs.append((localPlugins, localParser, localExcludedPlugins))
    else:
        for entry in configLocations:
            path = entry
            if not os.path.isfile(path):
                path = os.path.join(path, CFG_NAME)
                if not os.path.isfile(path):
                    # exception type?
                    raise Exception('Config file location %r could not be found'
                                    % entry)
            
            parser, plugins, excludedPlugins = loadPluginsConfigFile(path)
            configs.append((plugins, parser, excludedPlugins))
                    

    plugins = set(sum([plugin for plugin, _, __ in configs], []))
    parsers = [parser for _, parser, __ in configs]
    excludedPlugins = set(sum([excluded for _, __, excluded in configs], []))
    _config = combineConfigs(parsers)
    return plugins - excludedPlugins


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
        if value is RETURN_DEFAULT:
            return default
        return value

    def as_list(self, item, default=DEFAULT):
        value = self._get_value(item, default, allowEmpty=True)
        if value is RETURN_DEFAULT:
            return default
        return [line.strip() for line in value.splitlines()
                 if line.strip() and not line.strip().startswith('#')]

