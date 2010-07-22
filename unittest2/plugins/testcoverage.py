import unittest2
from unittest2.events import hooks, addOption, getConfig

import sys

try:
    import coverage
except ImportError:
    coverage = None



class CoveragePlugin(object):
    
    def start(self, event):
        self.initialModules = set(sys.modules.keys())
        coverage.erase()
        coverage.exclude('#pragma[: ]+[nN][oO] [cC][oO][vV][eE][rR]')
        coverage.start()

    def stop(self, event):
        coverage.stop()
        modules = [module
                    for name, module in sys.modules.items()
                    if name not in self.initialModules and
                    hasattr(module, '__file__') and
                    module.__file__ is not None and
                    not name.startswith('unittest2') and
                    not 'test' in name]
        coverage.report(modules, file=open('coverage.txt', 'w'))


def enable():
    _plugin = CoveragePlugin()
    hooks.testRunStart += _plugin.start
    hooks.testRunStop += _plugin.stop

ourOptions = getConfig('coverage')
alwaysOn = ourOptions.as_bool('always-on', default=False)

if coverage is not None:
    if alwaysOn:
        enable()
    else:
        help_text = 'Enable coverage reporting'
        addOption(enable, 'C', 'coverage', help_text)
