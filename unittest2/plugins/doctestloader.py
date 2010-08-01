from unittest2.config import getConfig
from unittest2.events import hooks, addOption

import doctest


def getDoctests(event):
    path = event.path
    if not path.lower().endswith('.txt'):
        return
    suite = doctest.DocFileTest(path, module_relative=False)
    event.extraTests.append(suite)

def enable():
    hooks.handleFile += getDoctests

ourOptions = getConfig('doctest')
alwaysOn = ourOptions.as_bool('always-on', default=False)


if alwaysOn:
    enable()
else:
    help_text = 'Load doctests from text files'
    addOption(enable, None, 'doctest', help_text)
