import unittest2
from unittest2.config import getConfig
from unittest2.events import hooks, addOption

import types


def loadModules(event):
    loader = event.loader
    module = event.module
    
    def is_test(obj):
        return obj.__name__.startswith(loader.testMethodPrefix)
    
    tests = []
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, types.FunctionType) and is_test(obj):
            args = {}
            setUp = getattr(obj, 'setUp', None)
            tearDown = getattr(obj, 'tearDown', None)
            if setUp is not None:
                args['setUp'] = setUp
            if tearDown is not None:
                args['tearDown'] = tearDown
            case = unittest2.FunctionTestCase(obj, **args)
            tests.append(case)
            
    event.extraTests.extend(tests)

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

def enable():
    hooks.loadTestsFromModule += loadModules

ourOptions = getConfig('module-loading')
alwaysOn = ourOptions.as_bool('always-on', default=False)

if alwaysOn:
    enable()
else:
    help_text = 'Load test functions from test modules'
    addOption(enable, None, 'test-functions', help_text)

