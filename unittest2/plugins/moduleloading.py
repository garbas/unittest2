import sys
from unittest2 import Plugin, FunctionTestCase, TestCase, TestSuite
from unittest2.util import getObjectFromName

import types

__unittest = True


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


def _make_load_test_failure(testname, exc_info):
    def testFailure(self):
        raise exc_info[0], exc_info[1], exc_info[2]
    classname = 'LoadingGeneratedTestFail'
    attrs = {testname: testFailure}
    TestClass = type(classname, (TestCase,), attrs)
    return TestSuite((TestClass(testname),))

class TestNotFoundError(Exception):
    pass

def testFromName(name, module):
    pos = name.find(':')
    index = None
    if pos != -1:
        real_name, digits = name[:pos], name[pos+1:]
        try:
            index = int(digits)
        except ValueError:
            pass
        else:
            name = real_name

    try:
        parent, obj = getObjectFromName(name, module)
    except AttributeError, ImportError:
        return None
    return parent, obj, name, index


class Functions(Plugin):
    
    generatorsEnabled = False
    parametersEnabled = False
    configSection = 'functions'
    commandLineSwitch = (None, 'functions', 'Load tests from functions')

    def loadTestsFromName(self, event):
        name = event.name
        module = event.module
        result = testFromName(name, module)
        if result is None:
            return
        parent, obj, name, index = result

        if isinstance(obj, types.FunctionType):
            suite = TestSuite()
            suite.addTests(self.createTests(obj, index))
            event.handled = True
            return suite


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
                tests.extend(self.createTests(obj))
        event.extraTests.extend(tests)

    def createTests(self, obj, testIndex=None):
        tests = []
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
        if testIndex is not None:
            # what if this doesn't exist?
            return [tests[testIndex-1]]
        return tests


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
                event.extraTests.extend(
                    testsFromGenerator(name, method(instance), testCaseClass)
                )

    def getTestCaseNames(self, event):
        names = filter(event.isTestMethod, dir(event.testCase))
        klass = event.testCase
        for name in names:
            method = getattr(klass, name)
            if getattr(method, 'testGenerator', None) is not None:
                event.excludedNames.append(name)

    def loadTestsFromName(self, event):
        original_name = name = event.name
        module = event.module
        result = testFromName(name, module)
        if result is None:
            # we can't find it - let the default case handle it
            return
        
        parent, obj, name, index = result
        if (index is None or not isinstance(parent, type) or 
            not issubclass(parent, TestCase) or 
            not getattr(obj, 'testGenerator', False)):
            # we're only handling TestCase generator methods here
            return

        instance = parent(obj.__name__)
        
        try:
            test = list(testsFromGenerator(name, obj(instance), parent))[index-1]
        except IndexError:
            raise TestNotFoundError(original_name)
        
        suite = TestSuite()
        suite.addTest(test)
        event.handled = True
        return suite


def testsFromGenerator(name, generator, testCaseClass):
    try:
        for index, (func, args) in enumerate(generator):
            method_name = name_from_args(name, index, args)
            setattr(testCaseClass, method_name, None)
            instance = testCaseClass(method_name)
            delattr(testCaseClass, method_name)
            def method(func=func, args=args):
                return func(*args)
            setattr(instance, method_name, method)
            yield instance
    except:
        exc_info = sys.exc_info()
        test_name = '%s.%s.%s' % (testCaseClass.__module__,
                                  testCaseClass.__name__,
                                  name)
        yield _make_load_test_failure(test_name, exc_info)

def name_from_args(name, index, args):
    summary = ', '.join(repr(arg) for arg in args)
    return '%s:%s\n%s' % (name, index + 1, summary[:79])


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

    def loadTestsFromName(self, event):
        original_name = name = event.name
        module = event.module
        result = testFromName(name, module)
        if result is None:
            return
        parent, obj, name, index = result
        if (index is None or not isinstance(parent, type) or 
            not issubclass(parent, TestCase)):
            # we're only handling TestCase methods here
            return
        
        paramList = getattr(obj, 'paramList', None)
        if paramList is None:
            return
        instance = parent(obj.__name__)
        method = getattr(instance, obj.__name__)
        
        try:
            args = list(method.paramList)[index-1]
        except IndexError:
            raise TestNotFoundError(original_name)
        def _method(self, method=method, args=args):
            return method(*args)
        method_name = name_from_args(name, index-1, args)
        setattr(parent, method_name, _method)
        
        suite = TestSuite()
        suite.addTest(parent(method_name))
        event.handled = True
        return suite
        