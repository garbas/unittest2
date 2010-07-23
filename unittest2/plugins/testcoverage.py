import unittest2
from unittest2.events import hooks, addOption, getConfig

import os
import sys

try:
    import coverage
except ImportError, e:
    coverage = None
    coverageImportError = e

def get_src(filename):
    if sys.platform.startswith('java') and filename.endswith('$py.class'):
        return '.'.join((filename[:-9], 'py'))
    base, ext = os.path.splitext(filename)
    if ext in ('.pyc', '.pyo', '.py'):
        return '.'.join((base, 'py'))
    return filename

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

        self.cov.exclude('#pragma[: ]+[nN][oO] [cC][oO][vV][eE][rR]')
        for line in excludeLines:
            self.cov.exclude(line)
            
        self.cov.start()

    def get_modules(self):
        allModules = set(modules + extraModules)
        if not allModules:
            return
        
        morfs = []
        for name, module in sys.modules.items():
            parts = []
            path = getattr(module, '__file__', None)
            if path is None:
                continue
            for part in name.split('.'):
                parts.append(part)
                this_name = '.'.join(parts)
                if this_name in allModules:
                    morfs.append(get_src(path))
                    continue
        return morfs

    def stop(self, event):
        self.cov.stop()
        args = dict(
            ignore_errors=ignoreErrors,
        )
        allModules = self.get_modules()
        if allModules:
            args['morfs'] = allModules
        if reportHtml:
            self.cov.html_report(directory=htmlDirectory, **args)
        else:
            self.cov.report(file=textFile, **args)


def enable():
    if coverage is None:
        raise coverageImportError
    _plugin = CoveragePlugin()
    #hooks.testRunStart += _plugin.start
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
excludeLines = ourOptions.as_list('exclude-lines', default=[])
ignoreErrors = ourOptions.as_bool('ignore-errors', default=False)
modules = ourOptions.as_list('modules', default=[])
extraModules = []

def initialise():
    if alwaysOn:
        enable()
    else:
        help_text1 = 'Enable coverage reporting'
        help_text2 = 'Specify a module or package for coverage reporting'
        addOption(enable, 'C', 'coverage', help_text1)
        addOption(extraModules, None, 'cover-module', help_text2)
