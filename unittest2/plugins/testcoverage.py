import unittest2
from unittest2.events import hooks, addOption, getConfig

import os
import sys

try:
    import coverage
except ImportError, coverageImportError:
    coverage = None



class CoveragePlugin(object):
    def __init__(self):
        args = dict(
            config_file=configFile,
            cover_pylib=False
        )
        if reportDirectory:
            args['directory'] = reportDirectory
        
        self.cov = coverage.coverage(**args)
        self.cov.erase()

    def start(self, event):
        self.cov.exclude('#pragma[: ]+[nN][oO] [cC][oO][vV][eE][rR]')
        self.cov.start()

    def stop(self, event):
        self.cov.stop()
        self.cov.html_report()


def enable():
    if coverage is None:
        raise coverageImportError
    _plugin = CoveragePlugin()
    hooks.testRunStart += _plugin.start
    hooks.testRunStop += _plugin.stop

ourOptions = getConfig('coverage')
alwaysOn = ourOptions.as_bool('always-on', default=False)
configFile = ourOptions.get('config', '').strip() or True
reportDirectory = ourOptions.get('directory', '').strip()

def initialise():
    if alwaysOn:
        enable()
    else:
        help_text = 'Enable coverage reporting'
        addOption(enable, 'C', 'coverage', help_text)
