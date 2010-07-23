import unittest2
from unittest2.events import hooks, addOption, getConfig

import os
import sys

try:
    import coverage
except ImportError, e:
    coverage = None
    coverageImportError = e



class CoveragePlugin(object):
    def __init__(self):
        args = dict(
            config_file=configFile,
            cover_pylib=False,
            branch=branch,
            timid=timid,
        )
        self.cov = coverage.coverage(**args)
        self.cov.erase()

    def start(self, event):
        self.cov.exclude('#pragma[: ]+[nN][oO] [cC][oO][vV][eE][rR]')
        self.cov.start()

    def stop(self, event):
        self.cov.stop()
        if reportHtml:
            self.cov.html_report(directory=htmlDirectory)
        else:
            self.cov.report(file=textFile)


def enable():
    if coverage is None:
        raise coverageImportError
    _plugin = CoveragePlugin()
    hooks.testRunStart += _plugin.start
    hooks.testRunStop += _plugin.stop

ourOptions = getConfig('coverage')
alwaysOn = ourOptions.as_bool('always-on', default=False)
configFile = ourOptions.get('config', '').strip() or True
htmlDirectory = ourOptions.get('html-directory', '').strip() or None
textFile = ourOptions.get('text-file', '').strip() or None
branch = ourOptions.as_bool('branch', default=None)
timid = ourOptions.as_bool('timid', default=False)
cover_pylib = ourOptions.as_bool('cover-pylib', default=False)
reportHtml = ourOptions.as_bool('report-html', default=True)

def initialise():
    if alwaysOn:
        enable()
    else:
        help_text = 'Enable coverage reporting'
        addOption(enable, 'C', 'coverage', help_text)
