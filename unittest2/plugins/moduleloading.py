from unittest2 import Plugin, FunctionTestCase

import types

help_text = 'Load test functions from test modules'
class TestLoading(Plugin):
    
    configSection = 'module-loading'
    commandLineSwitch = (None, 'test-functions', help_text)


    def loadTestsFromModule(self, event):
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
                case = FunctionTestCase(obj, **args)
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

def testGenerator(func):
    func.testGenerator = True
    return func