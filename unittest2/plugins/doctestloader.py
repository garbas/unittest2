from unittest2.events import hooks

import doctest


def getDoctests(event):
    path = event.path
    if not path.lower().endswith('.txt'):
        return
    suite = doctest.DocFileTest(path, module_relative=False)
    event.extraTests.append(suite)

hooks.handleFile += getDoctests
