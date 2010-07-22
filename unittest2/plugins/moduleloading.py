import unittest2
from unittest2.events import hooks

import types


def loadModules(event):
    loader = event.loader
    module = event.module
    event.handled = True
    
    def is_test(obj):
        return obj.__name__.startswith(loader.testMethodPrefix)
    
    tests = []
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and issubclass(obj, unittest2.TestCase):
            tests.append(loader.loadTestsFromTestCase(obj))
        elif isinstance(obj, types.FunctionType) and is_test(obj):
            case = unittest2.FunctionTestCase(obj)
            tests.append(case)
    return loader.suiteClass(tests)

hooks.loadTestsFromModule += loadModules
