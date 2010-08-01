from unittest2.events import Plugin, addOption
from unittest2.util import getSource

import os
import sys

try:
    import coverage
except ImportError, e:
    coverage = None
    coverageImportError = e


help_text1 = 'Enable coverage reporting'
help_text2 = 'Specify a module or package for coverage reporting'

class CoveragePlugin(Plugin):
    
    configSection = 'coverage'
    commandLineSwitch = ('C', 'coverage', help_text1)
    
    def __init__(self):
        self.configFile = self.config.get('config', '').strip() or True
        self.htmlDirectory = self.config.get('html-directory', '').strip() or None
        self.textFile = self.config.get('text-file', '').strip() or None
        self.branch = self.config.as_bool('branch', default=None)
        self.timid = self.config.as_bool('timid', default=False)
        self.cover_pylib = self.config.as_bool('cover-pylib', default=False)
        self.reportHtml = self.config.as_bool('report-html', default=True)
        self.excludeLines = self.config.as_list('exclude-lines', default=[])
        self.ignoreErrors = self.config.as_bool('ignore-errors', default=False)
        self.modules = self.config.as_list('modules', default=[])
        self.annotate  = self.config.as_bool('annotate', default=False)
        
        addOption(self.modules, None, 'cover-module', help_text2)
    
    def register(self):
        if coverage is None:
            raise coverageImportError
        Plugin.register(self)
    
    def pluginsLoaded(self, event):
        args = dict(
            config_file=self.configFile,
            cover_pylib=False,
            branch=self.branch,
            timid=self.timid,
        )
        self.cov = coverage.coverage(**args)
        self.cov.erase()

        self.cov.exclude('#pragma[: ]+[nN][oO] [cC][oO][vV][eE][rR]')
        for line in self.excludeLines:
            self.cov.exclude(line)
            
        self.cov.start()

    def get_modules(self):
        allModules = set(self.modules)
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
                    morfs.append(getSource(path))
                    continue
        return morfs

    def stopTestRun(self, event):
        self.cov.stop()
        args = dict(
            ignore_errors=self.ignoreErrors,
        )
        allModules = self.get_modules()
        if allModules:
            args['morfs'] = allModules
        if self.reportHtml:
            self.cov.html_report(directory=self.htmlDirectory, **args)
        else:
            handle = None
            if self.textFile:
                handle = open(self.textFile, 'w')
            self.cov.report(file=handle, **args)
            
            directory = None
            if self.textFile is not None:
                directory= os.path.dirname(self.textFile)
            if self.annotate:
                self.cov.annotate(morfs=allModules, directory=directory)


