from unittest2.events import Plugin, addOption, getConfig

import pdb
import sys


class Debugger(Plugin):

    def __init__(self):
        ourOptions = getConfig('debugger')
        self.errorsOnly = ourOptions.as_bool('errors-only', default=False)
        
        alwaysOn = ourOptions.as_bool('always-on', default=False)
        if alwaysOn:
            self.register()
        else:
            help_text = 'Enter pdb on test fail or error'
            addOption(self.register, 'D', 'debugger', help_text)

    def onTestFail(self, event):
        value, tb = event.exc_info[1:]
        test = event.test
        if self.errorsOnly and isinstance(value, test.failureException):
            return
        original = sys.stdout
        sys.stdout = sys.__stdout__
        try:
            pdb.post_mortem(tb)
        finally:
            sys.stdout = original
