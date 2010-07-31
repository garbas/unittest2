from unittest2.events import Plugin

import pdb
import sys


class Debugger(Plugin):

    configSection = 'debugger'
    commandLineSwitch = ('D', 'debugger', 'Enter pdb on test fail or error')
    
    def __init__(self):
        self.errorsOnly = self.config.as_bool('errors-only', default=False)
        

    def onTestFail(self, event):
        if event.internal:
            # skipped tests, unexpected successes, expected failures
            return
        
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
