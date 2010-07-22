import unittest2
from unittest2.events import hooks, addOption, getConfig

import pdb
import sys


def onTestFail(event):
    value, tb = event.exc_info[1:]
    test = event.test
    if isinstance(value, unittest2.SkipTest):
        return
    if errorsOnly and isinstance(value, test.failureException):
        return
    original = sys.stdout
    sys.stdout = sys.__stdout__
    try:
        pdb.post_mortem(tb)
    finally:
        sys.stdout = original


def enable():
    hooks.onTestFail += onTestFail

ourOptions = getConfig('debugger')
alwaysOn = ourOptions.as_bool('always-on', default=False)
errorsOnly = ourOptions.as_bool('errors-only', default=False)

if alwaysOn:
    enable()
else:
    help_text = 'Enter pdb on test fail or error'
    addOption(enable, 'D', 'debugger', help_text)