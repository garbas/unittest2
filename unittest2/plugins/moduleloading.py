from unittest2.events import hooks


def loadModules(event):
    pass

hooks.loadTestsFromModule += loadModules
