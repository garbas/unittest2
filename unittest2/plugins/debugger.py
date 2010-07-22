import unittest2
from unittest2.events import hooks, addOption, getConfig

import pdb


def onTestFail(event):
    value, tb = event.exc_info[1:]
    if isinstance(value, unittest2.SkipTest):
        return
    pdb.post_mortem(tb)


def enable():
    hooks.onTestFail += onTestFail

options = getConfig()

alwaysOn = False
ourOptions = options.get('debugger', {})
if 'always-on' in ourOptions:
    alwaysOn = ourOptions.as_bool('always-on')

if alwaysOn:
    enable()
else:
    help_text = 'Enter pdb on test fail or error'
    addOption(enable, 'D', 'debugger', help_text)