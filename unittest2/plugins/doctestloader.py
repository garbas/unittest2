from unittest2.events import events

import doctest


def getDoctests(event):
    path = event.path
    if not path.lower().endswith('.txt'):
        return
    event.handled = True
    return doctest.DocFileTest(path, module_relative=False)


events.handleFile += getDoctests
