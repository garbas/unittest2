import unittest2
from unittest2.events import hooks

import types


def loadModules(event):
    loader = event.loader
    module = event.module
    
    def is_test(obj):
        return obj.__name__.startswith(loader.testMethodPrefix)
    
    tests = []
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and issubclass(obj, unittest2.TestCase):
            tests.append(loader.loadTestsFromTestCase(obj))
        elif isinstance(obj, types.FunctionType) and is_test(obj):
            args = {}
            setUp = getattr(obj, 'setUp', None)
            tearDown = getattr(obj, 'tearDown', None)
            if setUp is not None:
                args['setUp'] = setUp
            if tearDown is not None:
                args['tearDown'] = tearDown
            case = unittest2.FunctionTestCase(obj, **args)
            tests.append(case)
    event.extraTests = tests

hooks.loadTestsFromModule += loadModules

def setUp(setupFunction):
    def decorator(func):
        func.setUp = setupFunction
        return func
    return decorator

def tearDown(tearDownFunction):
    def decorator(func):
        func.tearDown = tearDownFunction
        return func
    return decorator