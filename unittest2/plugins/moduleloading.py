from unittest2 import Plugin, FunctionTestCase, TestCase

import types


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

def params(*paramList):
    def decorator(func):
        func.paramList = paramList
        return func
    return decorator


class Functions(Plugin):
    
    generatorsEnabled = False
    parametersEnabled = False
    configSection = 'functions'
    commandLineSwitch = (None, 'functions', 'Load tests from functions')

    def loadTestsFromModule(self, event):
        loader = event.loader
        module = event.module
        
        def is_test(obj):
            if obj is testGenerator:
                return False
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
                
                paramList = getattr(obj, 'paramList', None)
                isGenerator = getattr(obj, 'testGenerator', False)
                if self.parametersEnabled and paramList is not None:
                    for index, argSet in enumerate(paramList):
                        def func(argSet=argSet, obj=obj):
                            return obj(*argSet)
                        name = '%s.%s' % (obj.__module__, obj.__name__)
                        func_name = name_from_args(name, index, argSet)
                        case = ParamsFunctionCase(func_name, func, **args)
                        tests.append(case)
                elif self.generatorsEnabled and isGenerator:
                    extras = list(obj())
                    name = '%s.%s' % (obj.__module__, obj.__name__)
                    def createTest(name):
                        return GeneratorFunctionCase(name, **args)
                    tests.extend(testsFromGenerator(name, extras, createTest))
                else:
                    case = FunctionTestCase(obj, **args)
                    tests.append(case)
                
        event.extraTests.extend(tests)


class GeneratorFunctionCase(FunctionTestCase):
    def __init__(self, name, **args):
        self._name = name
        FunctionTestCase.__init__(self, None, **args)

    _testFunc = property(lambda self: getattr(self, self._name),
                         lambda self, func: None)

    def __repr__(self):
        return self._name

    id = __str__ = __repr__

class ParamsFunctionCase(FunctionTestCase):
    def __init__(self, name, func, **args):
        self._name = name
        FunctionTestCase.__init__(self, func, **args)
        
    def __repr__(self):
        return self._name

    id = __str__ = __repr__

class Generators(Plugin):

    configSection = 'generators'
    commandLineSwitch = (None, 'generators', 'Load tests from generators')

    def pluginsLoaded(self, event):
        Functions.generatorsEnabled = True
        
    def loadTestsFromTestCase(self, event):
        testCaseClass = event.testCase
        for name in dir(testCaseClass):
            method = getattr(testCaseClass, name)
            if getattr(method, 'testGenerator', None) is not None:
                instance = testCaseClass(name)
                tests = list(method(instance))
                event.extraTests.extend(
                    testsFromGenerator(name, tests, testCaseClass)
                )

    def getTestCaseNames(self, event):
        names = filter(event.isTestMethod, dir(event.testCase))
        klass = event.testCase
        for name in names:
            method = getattr(klass, name)
            if getattr(method, 'testGenerator', None) is not None:
                event.excludedNames.append(name)

def testsFromGenerator(name, tests, testCaseClass):
    for index, (func, args) in enumerate(tests):
        method_name = name_from_args(name, index, args)
        setattr(testCaseClass, method_name, None)
        instance = testCaseClass(method_name)
        delattr(testCaseClass, method_name)
        def method(func=func, args=args):
            return func(*args)
        setattr(instance, method_name, method)
        yield instance

def name_from_args(name, index, args):
    summary = ', '.join(repr(arg) for arg in args)
    return '%s_%s\n%s' % (name, index + 1, summary[:79])


class Parameters(Plugin):
    configSection = 'parameters'
    commandLineSwitch = (None, 'params', 'Enable parameterised tests')

    def pluginsLoaded(self, event):
        Functions.parametersEnabled = True

    def getTestCaseNames(self, event):
        names = filter(event.isTestMethod, dir(event.testCase))
        klass = event.testCase
        for name in names:
            method = getattr(klass, name)
            paramList = getattr(method, 'paramList', None)
            if paramList is None:
                continue

            event.excludedNames.append(name)
            for index, args in enumerate(method.paramList):
                def _method(self, method=method, args=args):
                    return method(self, *args)
                method_name = name_from_args(name, index, args)
                setattr(klass, method_name, _method)
