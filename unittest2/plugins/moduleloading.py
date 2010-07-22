from unittest2 import FunctionTestCase
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
        if isinstance(obj, type) and issubclass(obj, unittest.TestCase):
            tests.append(loader.loadTestsFromTestCase(obj))
        elif isinstance(obj, types.FunctionType) and is_test(obj):
            case = FunctionTestCase(obj)
            tests.append(case)
    return loader.suiteClass(tests)

hooks.loadTestsFromModule += loadModules
