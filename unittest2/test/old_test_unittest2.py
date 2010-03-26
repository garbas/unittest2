import os
import re
import sys

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

import unittest2
import types
from copy import deepcopy
from cStringIO import StringIO
import pickle

from unittest2.test.support import OldTestResult

### Support code
################################################################



# List subclass we can add attributes to.
class MyClassSuite(list):

    def __init__(self, tests):
        super(MyClassSuite, self).__init__(tests)



################################################################
### /Support code

class Test_TestLoader(unittest2.TestCase):

    ### Tests for TestLoader.loadTestsFromTestCase
    ################################################################

    # "Return a suite of all tests cases contained in the TestCase-derived
    # class testCaseClass"
    def test_loadTestsFromTestCase(self):
        class Foo(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass
            def foo_bar(self): pass

        tests = unittest2.TestSuite([Foo('test_1'), Foo('test_2')])

        loader = unittest2.TestLoader()
        self.assertEqual(loader.loadTestsFromTestCase(Foo), tests)

    # "Return a suite of all tests cases contained in the TestCase-derived
    # class testCaseClass"
    #
    # Make sure it does the right thing even if no tests were found
    def test_loadTestsFromTestCase__no_matches(self):
        class Foo(unittest2.TestCase):
            def foo_bar(self): pass

        empty_suite = unittest2.TestSuite()

        loader = unittest2.TestLoader()
        self.assertEqual(loader.loadTestsFromTestCase(Foo), empty_suite)

    # "Return a suite of all tests cases contained in the TestCase-derived
    # class testCaseClass"
    #
    # What happens if loadTestsFromTestCase() is given an object
    # that isn't a subclass of TestCase? Specifically, what happens
    # if testCaseClass is a subclass of TestSuite?
    #
    # This is checked for specifically in the code, so we better add a
    # test for it.
    def test_loadTestsFromTestCase__TestSuite_subclass(self):
        class NotATestCase(unittest2.TestSuite):
            pass

        loader = unittest2.TestLoader()
        try:
            loader.loadTestsFromTestCase(NotATestCase)
        except TypeError:
            pass
        else:
            self.fail('Should raise TypeError')

    # "Return a suite of all tests cases contained in the TestCase-derived
    # class testCaseClass"
    #
    # Make sure loadTestsFromTestCase() picks up the default test method
    # name (as specified by TestCase), even though the method name does
    # not match the default TestLoader.testMethodPrefix string
    def test_loadTestsFromTestCase__default_method_name(self):
        class Foo(unittest2.TestCase):
            def runTest(self):
                pass

        loader = unittest2.TestLoader()
        # This has to be false for the test to succeed
        self.assertFalse('runTest'.startswith(loader.testMethodPrefix))

        suite = loader.loadTestsFromTestCase(Foo)
        self.assertIsInstance(suite, loader.suiteClass)
        self.assertEqual(list(suite), [Foo('runTest')])

    ################################################################
    ### /Tests for TestLoader.loadTestsFromTestCase

    ### Tests for TestLoader.loadTestsFromModule
    ################################################################

    # "This method searches `module` for classes derived from TestCase"
    def test_loadTestsFromModule__TestCase_subclass(self):
        m = types.ModuleType('m')
        class MyTestCase(unittest2.TestCase):
            def test(self):
                pass
        m.testcase_1 = MyTestCase

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromModule(m)
        self.assertIsInstance(suite, loader.suiteClass)

        expected = [loader.suiteClass([MyTestCase('test')])]
        self.assertEqual(list(suite), expected)

    # "This method searches `module` for classes derived from TestCase"
    #
    # What happens if no tests are found (no TestCase instances)?
    def test_loadTestsFromModule__no_TestCase_instances(self):
        m = types.ModuleType('m')

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromModule(m)
        self.assertIsInstance(suite, loader.suiteClass)
        self.assertEqual(list(suite), [])

    # "This method searches `module` for classes derived from TestCase"
    #
    # What happens if no tests are found (TestCases instances, but no tests)?
    def test_loadTestsFromModule__no_TestCase_tests(self):
        m = types.ModuleType('m')
        class MyTestCase(unittest2.TestCase):
            pass
        m.testcase_1 = MyTestCase

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromModule(m)
        self.assertIsInstance(suite, loader.suiteClass)

        self.assertEqual(list(suite), [loader.suiteClass()])

    # "This method searches `module` for classes derived from TestCase"s
    #
    # What happens if loadTestsFromModule() is given something other
    # than a module?
    #
    # XXX Currently, it succeeds anyway. This flexibility
    # should either be documented or loadTestsFromModule() should
    # raise a TypeError
    #
    # XXX Certain people are using this behaviour. We'll add a test for it
    def test_loadTestsFromModule__not_a_module(self):
        class MyTestCase(unittest2.TestCase):
            def test(self):
                pass

        class NotAModule(object):
            test_2 = MyTestCase

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromModule(NotAModule)

        reference = [unittest2.TestSuite([MyTestCase('test')])]
        self.assertEqual(list(suite), reference)


    # Check that loadTestsFromModule honors (or not) a module
    # with a load_tests function.
    def test_loadTestsFromModule__load_tests(self):
        m = types.ModuleType('m')
        class MyTestCase(unittest2.TestCase):
            def test(self):
                pass
        m.testcase_1 = MyTestCase

        load_tests_args = []
        def load_tests(loader, tests, pattern):
            self.assertIsInstance(tests, unittest2.TestSuite)
            load_tests_args.extend((loader, tests, pattern))
            return tests
        m.load_tests = load_tests

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromModule(m)
        self.assertIsInstance(suite, unittest2.TestSuite)
        self.assertEquals(load_tests_args, [loader, suite, None])

        load_tests_args = []
        suite = loader.loadTestsFromModule(m, use_load_tests=False)
        self.assertEquals(load_tests_args, [])

    def test_loadTestsFromModule__faulty_load_tests(self):
        m = types.ModuleType('m')

        def load_tests(loader, tests, pattern):
            raise TypeError('some failure')
        m.load_tests = load_tests

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromModule(m)
        self.assertIsInstance(suite, unittest2.TestSuite)
        self.assertEqual(suite.countTestCases(), 1)
        test = list(suite)[0]
        
        self.assertRaisesRegexp(TypeError, "some failure", test.m)
        

    ################################################################
    ### /Tests for TestLoader.loadTestsFromModule()

    ### Tests for TestLoader.loadTestsFromName()
    ################################################################

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    #
    # Is ValueError raised in response to an empty name?
    def test_loadTestsFromName__empty_name(self):
        loader = unittest2.TestLoader()

        try:
            loader.loadTestsFromName('')
        except ValueError, e:
            self.assertEqual(str(e), "Empty module name")
        else:
            self.fail("TestLoader.loadTestsFromName failed to raise ValueError")

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    #
    # What happens when the name contains invalid characters?
    def test_loadTestsFromName__malformed_name(self):
        loader = unittest2.TestLoader()

        # XXX Should this raise ValueError or ImportError?
        try:
            loader.loadTestsFromName('abc () //')
        except ValueError:
            pass
        except ImportError:
            pass
        else:
            self.fail("TestLoader.loadTestsFromName failed to raise ValueError")

    # "The specifier name is a ``dotted name'' that may resolve ... to a
    # module"
    #
    # What happens when a module by that name can't be found?
    def test_loadTestsFromName__unknown_module_name(self):
        loader = unittest2.TestLoader()

        try:
            loader.loadTestsFromName('sdasfasfasdf')
        except ImportError, e:
            self.assertEqual(str(e), "No module named sdasfasfasdf")
        else:
            self.fail("TestLoader.loadTestsFromName failed to raise ImportError")

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    #
    # What happens when the module is found, but the attribute can't?
    def test_loadTestsFromName__unknown_attr_name(self):
        loader = unittest2.TestLoader()

        try:
            loader.loadTestsFromName('unittest2.sdasfasfasdf')
        except AttributeError, e:
            self.assertEqual(str(e), "'module' object has no attribute 'sdasfasfasdf'")
        else:
            self.fail("TestLoader.loadTestsFromName failed to raise AttributeError")

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    #
    # What happens when we provide the module, but the attribute can't be
    # found?
    def test_loadTestsFromName__relative_unknown_name(self):
        loader = unittest2.TestLoader()

        try:
            loader.loadTestsFromName('sdasfasfasdf', unittest2)
        except AttributeError, e:
            self.assertEqual(str(e), "'module' object has no attribute 'sdasfasfasdf'")
        else:
            self.fail("TestLoader.loadTestsFromName failed to raise AttributeError")

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    # ...
    # "The method optionally resolves name relative to the given module"
    #
    # Does loadTestsFromName raise ValueError when passed an empty
    # name relative to a provided module?
    #
    # XXX Should probably raise a ValueError instead of an AttributeError
    def test_loadTestsFromName__relative_empty_name(self):
        loader = unittest2.TestLoader()

        try:
            loader.loadTestsFromName('', unittest2)
        except AttributeError:
            pass
        else:
            self.fail("Failed to raise AttributeError")

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    # ...
    # "The method optionally resolves name relative to the given module"
    #
    # What happens when an impossible name is given, relative to the provided
    # `module`?
    def test_loadTestsFromName__relative_malformed_name(self):
        loader = unittest2.TestLoader()

        # XXX Should this raise AttributeError or ValueError?
        try:
            loader.loadTestsFromName('abc () //', unittest2)
        except ValueError:
            pass
        except AttributeError:
            pass
        else:
            self.fail("TestLoader.loadTestsFromName failed to raise ValueError")

    # "The method optionally resolves name relative to the given module"
    #
    # Does loadTestsFromName raise TypeError when the `module` argument
    # isn't a module object?
    #
    # XXX Accepts the not-a-module object, ignorning the object's type
    # This should raise an exception or the method name should be changed
    #
    # XXX Some people are relying on this, so keep it for now
    def test_loadTestsFromName__relative_not_a_module(self):
        class MyTestCase(unittest2.TestCase):
            def test(self):
                pass

        class NotAModule(object):
            test_2 = MyTestCase

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromName('test_2', NotAModule)

        reference = [MyTestCase('test')]
        self.assertEqual(list(suite), reference)

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    #
    # Does it raise an exception if the name resolves to an invalid
    # object?
    def test_loadTestsFromName__relative_bad_object(self):
        m = types.ModuleType('m')
        m.testcase_1 = object()

        loader = unittest2.TestLoader()
        try:
            loader.loadTestsFromName('testcase_1', m)
        except TypeError:
            pass
        else:
            self.fail("Should have raised TypeError")

    # "The specifier name is a ``dotted name'' that may
    # resolve either to ... a test case class"
    def test_loadTestsFromName__relative_TestCase_subclass(self):
        m = types.ModuleType('m')
        class MyTestCase(unittest2.TestCase):
            def test(self):
                pass
        m.testcase_1 = MyTestCase

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromName('testcase_1', m)
        self.assertIsInstance(suite, loader.suiteClass)
        self.assertEqual(list(suite), [MyTestCase('test')])

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    def test_loadTestsFromName__relative_TestSuite(self):
        m = types.ModuleType('m')
        class MyTestCase(unittest2.TestCase):
            def test(self):
                pass
        m.testsuite = unittest2.TestSuite([MyTestCase('test')])

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromName('testsuite', m)
        self.assertIsInstance(suite, loader.suiteClass)

        self.assertEqual(list(suite), [MyTestCase('test')])

    # "The specifier name is a ``dotted name'' that may resolve ... to
    # ... a test method within a test case class"
    def test_loadTestsFromName__relative_testmethod(self):
        m = types.ModuleType('m')
        class MyTestCase(unittest2.TestCase):
            def test(self):
                pass
        m.testcase_1 = MyTestCase

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromName('testcase_1.test', m)
        self.assertIsInstance(suite, loader.suiteClass)

        self.assertEqual(list(suite), [MyTestCase('test')])

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    #
    # Does loadTestsFromName() raise the proper exception when trying to
    # resolve "a test method within a test case class" that doesn't exist
    # for the given name (relative to a provided module)?
    def test_loadTestsFromName__relative_invalid_testmethod(self):
        m = types.ModuleType('m')
        class MyTestCase(unittest2.TestCase):
            def test(self):
                pass
        m.testcase_1 = MyTestCase

        loader = unittest2.TestLoader()
        try:
            loader.loadTestsFromName('testcase_1.testfoo', m)
        except AttributeError, e:
            self.assertEqual(str(e), "type object 'MyTestCase' has no attribute 'testfoo'")
        else:
            self.fail("Failed to raise AttributeError")

    # "The specifier name is a ``dotted name'' that may resolve ... to
    # ... a callable object which returns a ... TestSuite instance"
    def test_loadTestsFromName__callable__TestSuite(self):
        m = types.ModuleType('m')
        testcase_1 = unittest2.FunctionTestCase(lambda: None)
        testcase_2 = unittest2.FunctionTestCase(lambda: None)
        def return_TestSuite():
            return unittest2.TestSuite([testcase_1, testcase_2])
        m.return_TestSuite = return_TestSuite

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromName('return_TestSuite', m)
        self.assertIsInstance(suite, loader.suiteClass)
        self.assertEqual(list(suite), [testcase_1, testcase_2])

    # "The specifier name is a ``dotted name'' that may resolve ... to
    # ... a callable object which returns a TestCase ... instance"
    def test_loadTestsFromName__callable__TestCase_instance(self):
        m = types.ModuleType('m')
        testcase_1 = unittest2.FunctionTestCase(lambda: None)
        def return_TestCase():
            return testcase_1
        m.return_TestCase = return_TestCase

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromName('return_TestCase', m)
        self.assertIsInstance(suite, loader.suiteClass)
        self.assertEqual(list(suite), [testcase_1])

    # "The specifier name is a ``dotted name'' that may resolve ... to
    # ... a callable object which returns a TestCase ... instance"
    #*****************************************************************
    #Override the suiteClass attribute to ensure that the suiteClass
    #attribute is used
    def test_loadTestsFromName__callable__TestCase_instance_ProperSuiteClass(self):
        class SubTestSuite(unittest2.TestSuite):
            pass
        m = types.ModuleType('m')
        testcase_1 = unittest2.FunctionTestCase(lambda: None)
        def return_TestCase():
            return testcase_1
        m.return_TestCase = return_TestCase

        loader = unittest2.TestLoader()
        loader.suiteClass = SubTestSuite
        suite = loader.loadTestsFromName('return_TestCase', m)
        self.assertIsInstance(suite, loader.suiteClass)
        self.assertEqual(list(suite), [testcase_1])

    # "The specifier name is a ``dotted name'' that may resolve ... to
    # ... a test method within a test case class"
    #*****************************************************************
    #Override the suiteClass attribute to ensure that the suiteClass
    #attribute is used
    def test_loadTestsFromName__relative_testmethod_ProperSuiteClass(self):
        class SubTestSuite(unittest2.TestSuite):
            pass
        m = types.ModuleType('m')
        class MyTestCase(unittest2.TestCase):
            def test(self):
                pass
        m.testcase_1 = MyTestCase

        loader = unittest2.TestLoader()
        loader.suiteClass=SubTestSuite
        suite = loader.loadTestsFromName('testcase_1.test', m)
        self.assertIsInstance(suite, loader.suiteClass)

        self.assertEqual(list(suite), [MyTestCase('test')])

    # "The specifier name is a ``dotted name'' that may resolve ... to
    # ... a callable object which returns a TestCase or TestSuite instance"
    #
    # What happens if the callable returns something else?
    def test_loadTestsFromName__callable__wrong_type(self):
        m = types.ModuleType('m')
        def return_wrong():
            return 6
        m.return_wrong = return_wrong

        loader = unittest2.TestLoader()
        try:
            loader.loadTestsFromName('return_wrong', m)
        except TypeError:
            pass
        else:
            self.fail("TestLoader.loadTestsFromName failed to raise TypeError")

    # "The specifier can refer to modules and packages which have not been
    # imported; they will be imported as a side-effect"
    def test_loadTestsFromName__module_not_loaded(self):
        # We're going to try to load this module as a side-effect, so it
        # better not be loaded before we try.
        #
        # Why pick audioop? Google shows it isn't used very often, so there's
        # a good chance that it won't be imported when this test is run
        module_name = 'audioop'

        if module_name in sys.modules:
            del sys.modules[module_name]

        loader = unittest2.TestLoader()
        try:
            suite = loader.loadTestsFromName(module_name)

            self.assertIsInstance(suite, loader.suiteClass)
            self.assertEqual(list(suite), [])

            # audioop should now be loaded, thanks to loadTestsFromName()
            self.assertIn(module_name, sys.modules)
        finally:
            if module_name in sys.modules:
                del sys.modules[module_name]

    ################################################################
    ### Tests for TestLoader.loadTestsFromName()

    ### Tests for TestLoader.loadTestsFromNames()
    ################################################################

    # "Similar to loadTestsFromName(), but takes a sequence of names rather
    # than a single name."
    #
    # What happens if that sequence of names is empty?
    def test_loadTestsFromNames__empty_name_list(self):
        loader = unittest2.TestLoader()

        suite = loader.loadTestsFromNames([])
        self.assertIsInstance(suite, loader.suiteClass)
        self.assertEqual(list(suite), [])

    # "Similar to loadTestsFromName(), but takes a sequence of names rather
    # than a single name."
    # ...
    # "The method optionally resolves name relative to the given module"
    #
    # What happens if that sequence of names is empty?
    #
    # XXX Should this raise a ValueError or just return an empty TestSuite?
    def test_loadTestsFromNames__relative_empty_name_list(self):
        loader = unittest2.TestLoader()

        suite = loader.loadTestsFromNames([], unittest2)
        self.assertIsInstance(suite, loader.suiteClass)
        self.assertEqual(list(suite), [])

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    #
    # Is ValueError raised in response to an empty name?
    def test_loadTestsFromNames__empty_name(self):
        loader = unittest2.TestLoader()

        try:
            loader.loadTestsFromNames([''])
        except ValueError, e:
            self.assertEqual(str(e), "Empty module name")
        else:
            self.fail("TestLoader.loadTestsFromNames failed to raise ValueError")

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    #
    # What happens when presented with an impossible module name?
    def test_loadTestsFromNames__malformed_name(self):
        loader = unittest2.TestLoader()

        # XXX Should this raise ValueError or ImportError?
        try:
            loader.loadTestsFromNames(['abc () //'])
        except ValueError:
            pass
        except ImportError:
            pass
        else:
            self.fail("TestLoader.loadTestsFromNames failed to raise ValueError")

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    #
    # What happens when no module can be found for the given name?
    def test_loadTestsFromNames__unknown_module_name(self):
        loader = unittest2.TestLoader()

        try:
            loader.loadTestsFromNames(['sdasfasfasdf'])
        except ImportError, e:
            self.assertEqual(str(e), "No module named sdasfasfasdf")
        else:
            self.fail("TestLoader.loadTestsFromNames failed to raise ImportError")

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    #
    # What happens when the module can be found, but not the attribute?
    def test_loadTestsFromNames__unknown_attr_name(self):
        loader = unittest2.TestLoader()

        try:
            loader.loadTestsFromNames(['unittest2.sdasfasfasdf', 'unittest2'])
        except AttributeError, e:
            self.assertEqual(str(e), "'module' object has no attribute 'sdasfasfasdf'")
        else:
            self.fail("TestLoader.loadTestsFromNames failed to raise AttributeError")

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    # ...
    # "The method optionally resolves name relative to the given module"
    #
    # What happens when given an unknown attribute on a specified `module`
    # argument?
    def test_loadTestsFromNames__unknown_name_relative_1(self):
        loader = unittest2.TestLoader()

        try:
            loader.loadTestsFromNames(['sdasfasfasdf'], unittest2)
        except AttributeError, e:
            self.assertEqual(str(e), "'module' object has no attribute 'sdasfasfasdf'")
        else:
            self.fail("TestLoader.loadTestsFromName failed to raise AttributeError")

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    # ...
    # "The method optionally resolves name relative to the given module"
    #
    # Do unknown attributes (relative to a provided module) still raise an
    # exception even in the presence of valid attribute names?
    def test_loadTestsFromNames__unknown_name_relative_2(self):
        loader = unittest2.TestLoader()

        try:
            loader.loadTestsFromNames(['TestCase', 'sdasfasfasdf'], unittest2)
        except AttributeError, e:
            self.assertEqual(str(e), "'module' object has no attribute 'sdasfasfasdf'")
        else:
            self.fail("TestLoader.loadTestsFromName failed to raise AttributeError")

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    # ...
    # "The method optionally resolves name relative to the given module"
    #
    # What happens when faced with the empty string?
    #
    # XXX This currently raises AttributeError, though ValueError is probably
    # more appropriate
    def test_loadTestsFromNames__relative_empty_name(self):
        loader = unittest2.TestLoader()

        try:
            loader.loadTestsFromNames([''], unittest2)
        except AttributeError:
            pass
        else:
            self.fail("Failed to raise ValueError")

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    # ...
    # "The method optionally resolves name relative to the given module"
    #
    # What happens when presented with an impossible attribute name?
    def test_loadTestsFromNames__relative_malformed_name(self):
        loader = unittest2.TestLoader()

        # XXX Should this raise AttributeError or ValueError?
        try:
            loader.loadTestsFromNames(['abc () //'], unittest2)
        except AttributeError:
            pass
        except ValueError:
            pass
        else:
            self.fail("TestLoader.loadTestsFromNames failed to raise ValueError")

    # "The method optionally resolves name relative to the given module"
    #
    # Does loadTestsFromNames() make sure the provided `module` is in fact
    # a module?
    #
    # XXX This validation is currently not done. This flexibility should
    # either be documented or a TypeError should be raised.
    def test_loadTestsFromNames__relative_not_a_module(self):
        class MyTestCase(unittest2.TestCase):
            def test(self):
                pass

        class NotAModule(object):
            test_2 = MyTestCase

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromNames(['test_2'], NotAModule)

        reference = [unittest2.TestSuite([MyTestCase('test')])]
        self.assertEqual(list(suite), reference)

    # "The specifier name is a ``dotted name'' that may resolve either to
    # a module, a test case class, a TestSuite instance, a test method
    # within a test case class, or a callable object which returns a
    # TestCase or TestSuite instance."
    #
    # Does it raise an exception if the name resolves to an invalid
    # object?
    def test_loadTestsFromNames__relative_bad_object(self):
        m = types.ModuleType('m')
        m.testcase_1 = object()

        loader = unittest2.TestLoader()
        try:
            loader.loadTestsFromNames(['testcase_1'], m)
        except TypeError:
            pass
        else:
            self.fail("Should have raised TypeError")

    # "The specifier name is a ``dotted name'' that may resolve ... to
    # ... a test case class"
    def test_loadTestsFromNames__relative_TestCase_subclass(self):
        m = types.ModuleType('m')
        class MyTestCase(unittest2.TestCase):
            def test(self):
                pass
        m.testcase_1 = MyTestCase

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromNames(['testcase_1'], m)
        self.assertIsInstance(suite, loader.suiteClass)

        expected = loader.suiteClass([MyTestCase('test')])
        self.assertEqual(list(suite), [expected])

    # "The specifier name is a ``dotted name'' that may resolve ... to
    # ... a TestSuite instance"
    def test_loadTestsFromNames__relative_TestSuite(self):
        m = types.ModuleType('m')
        class MyTestCase(unittest2.TestCase):
            def test(self):
                pass
        m.testsuite = unittest2.TestSuite([MyTestCase('test')])

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromNames(['testsuite'], m)
        self.assertIsInstance(suite, loader.suiteClass)

        self.assertEqual(list(suite), [m.testsuite])

    # "The specifier name is a ``dotted name'' that may resolve ... to ... a
    # test method within a test case class"
    def test_loadTestsFromNames__relative_testmethod(self):
        m = types.ModuleType('m')
        class MyTestCase(unittest2.TestCase):
            def test(self):
                pass
        m.testcase_1 = MyTestCase

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromNames(['testcase_1.test'], m)
        self.assertIsInstance(suite, loader.suiteClass)

        ref_suite = unittest2.TestSuite([MyTestCase('test')])
        self.assertEqual(list(suite), [ref_suite])

    # "The specifier name is a ``dotted name'' that may resolve ... to ... a
    # test method within a test case class"
    #
    # Does the method gracefully handle names that initially look like they
    # resolve to "a test method within a test case class" but don't?
    def test_loadTestsFromNames__relative_invalid_testmethod(self):
        m = types.ModuleType('m')
        class MyTestCase(unittest2.TestCase):
            def test(self):
                pass
        m.testcase_1 = MyTestCase

        loader = unittest2.TestLoader()
        try:
            loader.loadTestsFromNames(['testcase_1.testfoo'], m)
        except AttributeError, e:
            self.assertEqual(str(e), "type object 'MyTestCase' has no attribute 'testfoo'")
        else:
            self.fail("Failed to raise AttributeError")

    # "The specifier name is a ``dotted name'' that may resolve ... to
    # ... a callable object which returns a ... TestSuite instance"
    def test_loadTestsFromNames__callable__TestSuite(self):
        m = types.ModuleType('m')
        testcase_1 = unittest2.FunctionTestCase(lambda: None)
        testcase_2 = unittest2.FunctionTestCase(lambda: None)
        def return_TestSuite():
            return unittest2.TestSuite([testcase_1, testcase_2])
        m.return_TestSuite = return_TestSuite

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromNames(['return_TestSuite'], m)
        self.assertIsInstance(suite, loader.suiteClass)

        expected = unittest2.TestSuite([testcase_1, testcase_2])
        self.assertEqual(list(suite), [expected])

    # "The specifier name is a ``dotted name'' that may resolve ... to
    # ... a callable object which returns a TestCase ... instance"
    def test_loadTestsFromNames__callable__TestCase_instance(self):
        m = types.ModuleType('m')
        testcase_1 = unittest2.FunctionTestCase(lambda: None)
        def return_TestCase():
            return testcase_1
        m.return_TestCase = return_TestCase

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromNames(['return_TestCase'], m)
        self.assertIsInstance(suite, loader.suiteClass)

        ref_suite = unittest2.TestSuite([testcase_1])
        self.assertEqual(list(suite), [ref_suite])

    # "The specifier name is a ``dotted name'' that may resolve ... to
    # ... a callable object which returns a TestCase or TestSuite instance"
    #
    # Are staticmethods handled correctly?
    def test_loadTestsFromNames__callable__call_staticmethod(self):
        m = types.ModuleType('m')
        class Test1(unittest2.TestCase):
            def test(self):
                pass

        testcase_1 = Test1('test')
        class Foo(unittest2.TestCase):
            @staticmethod
            def foo():
                return testcase_1
        m.Foo = Foo

        loader = unittest2.TestLoader()
        suite = loader.loadTestsFromNames(['Foo.foo'], m)
        self.assertIsInstance(suite, loader.suiteClass)

        ref_suite = unittest2.TestSuite([testcase_1])
        self.assertEqual(list(suite), [ref_suite])

    # "The specifier name is a ``dotted name'' that may resolve ... to
    # ... a callable object which returns a TestCase or TestSuite instance"
    #
    # What happens when the callable returns something else?
    def test_loadTestsFromNames__callable__wrong_type(self):
        m = types.ModuleType('m')
        def return_wrong():
            return 6
        m.return_wrong = return_wrong

        loader = unittest2.TestLoader()
        try:
            loader.loadTestsFromNames(['return_wrong'], m)
        except TypeError:
            pass
        else:
            self.fail("TestLoader.loadTestsFromNames failed to raise TypeError")

    # "The specifier can refer to modules and packages which have not been
    # imported; they will be imported as a side-effect"
    def test_loadTestsFromNames__module_not_loaded(self):
        # We're going to try to load this module as a side-effect, so it
        # better not be loaded before we try.
        #
        # Why pick audioop? Google shows it isn't used very often, so there's
        # a good chance that it won't be imported when this test is run
        module_name = 'audioop'

        if module_name in sys.modules:
            del sys.modules[module_name]

        loader = unittest2.TestLoader()
        try:
            suite = loader.loadTestsFromNames([module_name])

            self.assertIsInstance(suite, loader.suiteClass)
            self.assertEqual(list(suite), [unittest2.TestSuite()])

            # audioop should now be loaded, thanks to loadTestsFromName()
            self.assertIn(module_name, sys.modules)
        finally:
            if module_name in sys.modules:
                del sys.modules[module_name]

    ################################################################
    ### /Tests for TestLoader.loadTestsFromNames()

    ### Tests for TestLoader.getTestCaseNames()
    ################################################################

    # "Return a sorted sequence of method names found within testCaseClass"
    #
    # Test.foobar is defined to make sure getTestCaseNames() respects
    # loader.testMethodPrefix
    def test_getTestCaseNames(self):
        class Test(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass
            def foobar(self): pass

        loader = unittest2.TestLoader()

        self.assertEqual(loader.getTestCaseNames(Test), ['test_1', 'test_2'])

    # "Return a sorted sequence of method names found within testCaseClass"
    #
    # Does getTestCaseNames() behave appropriately if no tests are found?
    def test_getTestCaseNames__no_tests(self):
        class Test(unittest2.TestCase):
            def foobar(self): pass

        loader = unittest2.TestLoader()

        self.assertEqual(loader.getTestCaseNames(Test), [])

    # "Return a sorted sequence of method names found within testCaseClass"
    #
    # Are not-TestCases handled gracefully?
    #
    # XXX This should raise a TypeError, not return a list
    #
    # XXX It's too late in the 2.5 release cycle to fix this, but it should
    # probably be revisited for 2.6
    def test_getTestCaseNames__not_a_TestCase(self):
        class BadCase(int):
            def test_foo(self):
                pass

        loader = unittest2.TestLoader()
        names = loader.getTestCaseNames(BadCase)

        self.assertEqual(names, ['test_foo'])

    # "Return a sorted sequence of method names found within testCaseClass"
    #
    # Make sure inherited names are handled.
    #
    # TestP.foobar is defined to make sure getTestCaseNames() respects
    # loader.testMethodPrefix
    def test_getTestCaseNames__inheritance(self):
        class TestP(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass
            def foobar(self): pass

        class TestC(TestP):
            def test_1(self): pass
            def test_3(self): pass

        loader = unittest2.TestLoader()

        names = ['test_1', 'test_2', 'test_3']
        self.assertEqual(loader.getTestCaseNames(TestC), names)

    ################################################################
    ### /Tests for TestLoader.getTestCaseNames()

    ### Tests for TestLoader.testMethodPrefix
    ################################################################

    # "String giving the prefix of method names which will be interpreted as
    # test methods"
    #
    # Implicit in the documentation is that testMethodPrefix is respected by
    # all loadTestsFrom* methods.
    def test_testMethodPrefix__loadTestsFromTestCase(self):
        class Foo(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass
            def foo_bar(self): pass

        tests_1 = unittest2.TestSuite([Foo('foo_bar')])
        tests_2 = unittest2.TestSuite([Foo('test_1'), Foo('test_2')])

        loader = unittest2.TestLoader()
        loader.testMethodPrefix = 'foo'
        self.assertEqual(loader.loadTestsFromTestCase(Foo), tests_1)

        loader.testMethodPrefix = 'test'
        self.assertEqual(loader.loadTestsFromTestCase(Foo), tests_2)

    # "String giving the prefix of method names which will be interpreted as
    # test methods"
    #
    # Implicit in the documentation is that testMethodPrefix is respected by
    # all loadTestsFrom* methods.
    def test_testMethodPrefix__loadTestsFromModule(self):
        m = types.ModuleType('m')
        class Foo(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass
            def foo_bar(self): pass
        m.Foo = Foo

        tests_1 = [unittest2.TestSuite([Foo('foo_bar')])]
        tests_2 = [unittest2.TestSuite([Foo('test_1'), Foo('test_2')])]

        loader = unittest2.TestLoader()
        loader.testMethodPrefix = 'foo'
        self.assertEqual(list(loader.loadTestsFromModule(m)), tests_1)

        loader.testMethodPrefix = 'test'
        self.assertEqual(list(loader.loadTestsFromModule(m)), tests_2)

    # "String giving the prefix of method names which will be interpreted as
    # test methods"
    #
    # Implicit in the documentation is that testMethodPrefix is respected by
    # all loadTestsFrom* methods.
    def test_testMethodPrefix__loadTestsFromName(self):
        m = types.ModuleType('m')
        class Foo(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass
            def foo_bar(self): pass
        m.Foo = Foo

        tests_1 = unittest2.TestSuite([Foo('foo_bar')])
        tests_2 = unittest2.TestSuite([Foo('test_1'), Foo('test_2')])

        loader = unittest2.TestLoader()
        loader.testMethodPrefix = 'foo'
        self.assertEqual(loader.loadTestsFromName('Foo', m), tests_1)

        loader.testMethodPrefix = 'test'
        self.assertEqual(loader.loadTestsFromName('Foo', m), tests_2)

    # "String giving the prefix of method names which will be interpreted as
    # test methods"
    #
    # Implicit in the documentation is that testMethodPrefix is respected by
    # all loadTestsFrom* methods.
    def test_testMethodPrefix__loadTestsFromNames(self):
        m = types.ModuleType('m')
        class Foo(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass
            def foo_bar(self): pass
        m.Foo = Foo

        tests_1 = unittest2.TestSuite([unittest2.TestSuite([Foo('foo_bar')])])
        tests_2 = unittest2.TestSuite([Foo('test_1'), Foo('test_2')])
        tests_2 = unittest2.TestSuite([tests_2])

        loader = unittest2.TestLoader()
        loader.testMethodPrefix = 'foo'
        self.assertEqual(loader.loadTestsFromNames(['Foo'], m), tests_1)

        loader.testMethodPrefix = 'test'
        self.assertEqual(loader.loadTestsFromNames(['Foo'], m), tests_2)

    # "The default value is 'test'"
    def test_testMethodPrefix__default_value(self):
        loader = unittest2.TestLoader()
        self.assertTrue(loader.testMethodPrefix == 'test')

    ################################################################
    ### /Tests for TestLoader.testMethodPrefix

    ### Tests for TestLoader.sortTestMethodsUsing
    ################################################################

    # "Function to be used to compare method names when sorting them in
    # getTestCaseNames() and all the loadTestsFromX() methods"
    def test_sortTestMethodsUsing__loadTestsFromTestCase(self):
        def reversed_cmp(x, y):
            return -cmp(x, y)

        class Foo(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass

        loader = unittest2.TestLoader()
        loader.sortTestMethodsUsing = reversed_cmp

        tests = loader.suiteClass([Foo('test_2'), Foo('test_1')])
        self.assertEqual(loader.loadTestsFromTestCase(Foo), tests)

    # "Function to be used to compare method names when sorting them in
    # getTestCaseNames() and all the loadTestsFromX() methods"
    def test_sortTestMethodsUsing__loadTestsFromModule(self):
        def reversed_cmp(x, y):
            return -cmp(x, y)

        m = types.ModuleType('m')
        class Foo(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass
        m.Foo = Foo

        loader = unittest2.TestLoader()
        loader.sortTestMethodsUsing = reversed_cmp

        tests = [loader.suiteClass([Foo('test_2'), Foo('test_1')])]
        self.assertEqual(list(loader.loadTestsFromModule(m)), tests)

    # "Function to be used to compare method names when sorting them in
    # getTestCaseNames() and all the loadTestsFromX() methods"
    def test_sortTestMethodsUsing__loadTestsFromName(self):
        def reversed_cmp(x, y):
            return -cmp(x, y)

        m = types.ModuleType('m')
        class Foo(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass
        m.Foo = Foo

        loader = unittest2.TestLoader()
        loader.sortTestMethodsUsing = reversed_cmp

        tests = loader.suiteClass([Foo('test_2'), Foo('test_1')])
        self.assertEqual(loader.loadTestsFromName('Foo', m), tests)

    # "Function to be used to compare method names when sorting them in
    # getTestCaseNames() and all the loadTestsFromX() methods"
    def test_sortTestMethodsUsing__loadTestsFromNames(self):
        def reversed_cmp(x, y):
            return -cmp(x, y)

        m = types.ModuleType('m')
        class Foo(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass
        m.Foo = Foo

        loader = unittest2.TestLoader()
        loader.sortTestMethodsUsing = reversed_cmp

        tests = [loader.suiteClass([Foo('test_2'), Foo('test_1')])]
        self.assertEqual(list(loader.loadTestsFromNames(['Foo'], m)), tests)

    # "Function to be used to compare method names when sorting them in
    # getTestCaseNames()"
    #
    # Does it actually affect getTestCaseNames()?
    def test_sortTestMethodsUsing__getTestCaseNames(self):
        def reversed_cmp(x, y):
            return -cmp(x, y)

        class Foo(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass

        loader = unittest2.TestLoader()
        loader.sortTestMethodsUsing = reversed_cmp

        test_names = ['test_2', 'test_1']
        self.assertEqual(loader.getTestCaseNames(Foo), test_names)

    # "The default value is the built-in cmp() function"
    def test_sortTestMethodsUsing__default_value(self):
        loader = unittest2.TestLoader()
        self.assertTrue(loader.sortTestMethodsUsing is cmp)

    # "it can be set to None to disable the sort."
    #
    # XXX How is this different from reassigning cmp? Are the tests returned
    # in a random order or something? This behaviour should die
    def test_sortTestMethodsUsing__None(self):
        class Foo(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass

        loader = unittest2.TestLoader()
        loader.sortTestMethodsUsing = None

        test_names = ['test_2', 'test_1']
        self.assertEqual(set(loader.getTestCaseNames(Foo)), set(test_names))

    ################################################################
    ### /Tests for TestLoader.sortTestMethodsUsing

    ### Tests for TestLoader.suiteClass
    ################################################################

    # "Callable object that constructs a test suite from a list of tests."
    def test_suiteClass__loadTestsFromTestCase(self):
        class Foo(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass
            def foo_bar(self): pass

        tests = [Foo('test_1'), Foo('test_2')]

        loader = unittest2.TestLoader()
        loader.suiteClass = list
        self.assertEqual(loader.loadTestsFromTestCase(Foo), tests)

    # It is implicit in the documentation for TestLoader.suiteClass that
    # all TestLoader.loadTestsFrom* methods respect it. Let's make sure
    def test_suiteClass__loadTestsFromModule(self):
        m = types.ModuleType('m')
        class Foo(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass
            def foo_bar(self): pass
        m.Foo = Foo

        tests = [[Foo('test_1'), Foo('test_2')]]

        loader = unittest2.TestLoader()
        loader.suiteClass = list
        self.assertEqual(loader.loadTestsFromModule(m), tests)

    # It is implicit in the documentation for TestLoader.suiteClass that
    # all TestLoader.loadTestsFrom* methods respect it. Let's make sure
    def test_suiteClass__loadTestsFromName(self):
        m = types.ModuleType('m')
        class Foo(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass
            def foo_bar(self): pass
        m.Foo = Foo

        tests = [Foo('test_1'), Foo('test_2')]

        loader = unittest2.TestLoader()
        loader.suiteClass = list
        self.assertEqual(loader.loadTestsFromName('Foo', m), tests)

    # It is implicit in the documentation for TestLoader.suiteClass that
    # all TestLoader.loadTestsFrom* methods respect it. Let's make sure
    def test_suiteClass__loadTestsFromNames(self):
        m = types.ModuleType('m')
        class Foo(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass
            def foo_bar(self): pass
        m.Foo = Foo

        tests = [[Foo('test_1'), Foo('test_2')]]

        loader = unittest2.TestLoader()
        loader.suiteClass = list
        self.assertEqual(loader.loadTestsFromNames(['Foo'], m), tests)

    # "The default value is the TestSuite class"
    def test_suiteClass__default_value(self):
        loader = unittest2.TestLoader()
        self.assertTrue(loader.suiteClass is unittest2.TestSuite)

    ################################################################
    ### /Tests for TestLoader.suiteClass

### Support code for Test_TestSuite
################################################################

class Foo(unittest2.TestCase):
    def test_1(self): pass
    def test_2(self): pass
    def test_3(self): pass
    def runTest(self): pass

def _mk_TestSuite(*names):
    return unittest2.TestSuite(Foo(n) for n in names)

################################################################
### /Support code for Test_TestSuite

class Test_TestSuite(unittest2.TestCase, TestEquality):

    ### Set up attributes needed by inherited tests
    ################################################################

    # Used by TestEquality.test_eq
    eq_pairs = [(unittest2.TestSuite(), unittest2.TestSuite())
               ,(unittest2.TestSuite(), unittest2.TestSuite([]))
               ,(_mk_TestSuite('test_1'), _mk_TestSuite('test_1'))]

    # Used by TestEquality.test_ne
    ne_pairs = [(unittest2.TestSuite(), _mk_TestSuite('test_1'))
               ,(unittest2.TestSuite([]), _mk_TestSuite('test_1'))
               ,(_mk_TestSuite('test_1', 'test_2'), _mk_TestSuite('test_1', 'test_3'))
               ,(_mk_TestSuite('test_1'), _mk_TestSuite('test_2'))]

    ################################################################
    ### /Set up attributes needed by inherited tests

    ### Tests for TestSuite.__init__
    ################################################################

    # "class TestSuite([tests])"
    #
    # The tests iterable should be optional
    def test_init__tests_optional(self):
        suite = unittest2.TestSuite()

        self.assertEqual(suite.countTestCases(), 0)

    # "class TestSuite([tests])"
    # ...
    # "If tests is given, it must be an iterable of individual test cases
    # or other test suites that will be used to build the suite initially"
    #
    # TestSuite should deal with empty tests iterables by allowing the
    # creation of an empty suite
    def test_init__empty_tests(self):
        suite = unittest2.TestSuite([])

        self.assertEqual(suite.countTestCases(), 0)

    # "class TestSuite([tests])"
    # ...
    # "If tests is given, it must be an iterable of individual test cases
    # or other test suites that will be used to build the suite initially"
    #
    # TestSuite should allow any iterable to provide tests
    def test_init__tests_from_any_iterable(self):
        def tests():
            yield unittest2.FunctionTestCase(lambda: None)
            yield unittest2.FunctionTestCase(lambda: None)

        suite_1 = unittest2.TestSuite(tests())
        self.assertEqual(suite_1.countTestCases(), 2)

        suite_2 = unittest2.TestSuite(suite_1)
        self.assertEqual(suite_2.countTestCases(), 2)

        suite_3 = unittest2.TestSuite(set(suite_1))
        self.assertEqual(suite_3.countTestCases(), 2)

    # "class TestSuite([tests])"
    # ...
    # "If tests is given, it must be an iterable of individual test cases
    # or other test suites that will be used to build the suite initially"
    #
    # Does TestSuite() also allow other TestSuite() instances to be present
    # in the tests iterable?
    def test_init__TestSuite_instances_in_tests(self):
        def tests():
            ftc = unittest2.FunctionTestCase(lambda: None)
            yield unittest2.TestSuite([ftc])
            yield unittest2.FunctionTestCase(lambda: None)

        suite = unittest2.TestSuite(tests())
        self.assertEqual(suite.countTestCases(), 2)

    ################################################################
    ### /Tests for TestSuite.__init__

    # Container types should support the iter protocol
    def test_iter(self):
        test1 = unittest2.FunctionTestCase(lambda: None)
        test2 = unittest2.FunctionTestCase(lambda: None)
        suite = unittest2.TestSuite((test1, test2))

        self.assertEqual(list(suite), [test1, test2])

    # "Return the number of tests represented by the this test object.
    # ...this method is also implemented by the TestSuite class, which can
    # return larger [greater than 1] values"
    #
    # Presumably an empty TestSuite returns 0?
    def test_countTestCases_zero_simple(self):
        suite = unittest2.TestSuite()

        self.assertEqual(suite.countTestCases(), 0)

    # "Return the number of tests represented by the this test object.
    # ...this method is also implemented by the TestSuite class, which can
    # return larger [greater than 1] values"
    #
    # Presumably an empty TestSuite (even if it contains other empty
    # TestSuite instances) returns 0?
    def test_countTestCases_zero_nested(self):
        class Test1(unittest2.TestCase):
            def test(self):
                pass

        suite = unittest2.TestSuite([unittest2.TestSuite()])

        self.assertEqual(suite.countTestCases(), 0)

    # "Return the number of tests represented by the this test object.
    # ...this method is also implemented by the TestSuite class, which can
    # return larger [greater than 1] values"
    def test_countTestCases_simple(self):
        test1 = unittest2.FunctionTestCase(lambda: None)
        test2 = unittest2.FunctionTestCase(lambda: None)
        suite = unittest2.TestSuite((test1, test2))

        self.assertEqual(suite.countTestCases(), 2)

    # "Return the number of tests represented by the this test object.
    # ...this method is also implemented by the TestSuite class, which can
    # return larger [greater than 1] values"
    #
    # Make sure this holds for nested TestSuite instances, too
    def test_countTestCases_nested(self):
        class Test1(unittest2.TestCase):
            def test1(self): pass
            def test2(self): pass

        test2 = unittest2.FunctionTestCase(lambda: None)
        test3 = unittest2.FunctionTestCase(lambda: None)
        child = unittest2.TestSuite((Test1('test2'), test2))
        parent = unittest2.TestSuite((test3, child, Test1('test1')))

        self.assertEqual(parent.countTestCases(), 4)

    # "Run the tests associated with this suite, collecting the result into
    # the test result object passed as result."
    #
    # And if there are no tests? What then?
    def test_run__empty_suite(self):
        events = []
        result = LoggingResult(events)

        suite = unittest2.TestSuite()

        suite.run(result)

        self.assertEqual(events, [])

    # "Note that unlike TestCase.run(), TestSuite.run() requires the
    # "result object to be passed in."
    def test_run__requires_result(self):
        suite = unittest2.TestSuite()

        try:
            suite.run()
        except TypeError:
            pass
        else:
            self.fail("Failed to raise TypeError")

    # "Run the tests associated with this suite, collecting the result into
    # the test result object passed as result."
    def test_run(self):
        events = []
        result = LoggingResult(events)

        class LoggingCase(unittest2.TestCase):
            def run(self, result):
                events.append('run %s' % self._testMethodName)

            def test1(self): pass
            def test2(self): pass

        tests = [LoggingCase('test1'), LoggingCase('test2')]

        unittest2.TestSuite(tests).run(result)

        self.assertEqual(events, ['run test1', 'run test2'])

    # "Add a TestCase ... to the suite"
    def test_addTest__TestCase(self):
        class Foo(unittest2.TestCase):
            def test(self): pass

        test = Foo('test')
        suite = unittest2.TestSuite()

        suite.addTest(test)

        self.assertEqual(suite.countTestCases(), 1)
        self.assertEqual(list(suite), [test])

    # "Add a ... TestSuite to the suite"
    def test_addTest__TestSuite(self):
        class Foo(unittest2.TestCase):
            def test(self): pass

        suite_2 = unittest2.TestSuite([Foo('test')])

        suite = unittest2.TestSuite()
        suite.addTest(suite_2)

        self.assertEqual(suite.countTestCases(), 1)
        self.assertEqual(list(suite), [suite_2])

    # "Add all the tests from an iterable of TestCase and TestSuite
    # instances to this test suite."
    #
    # "This is equivalent to iterating over tests, calling addTest() for
    # each element"
    def test_addTests(self):
        class Foo(unittest2.TestCase):
            def test_1(self): pass
            def test_2(self): pass

        test_1 = Foo('test_1')
        test_2 = Foo('test_2')
        inner_suite = unittest2.TestSuite([test_2])

        def gen():
            yield test_1
            yield test_2
            yield inner_suite

        suite_1 = unittest2.TestSuite()
        suite_1.addTests(gen())

        self.assertEqual(list(suite_1), list(gen()))

        # "This is equivalent to iterating over tests, calling addTest() for
        # each element"
        suite_2 = unittest2.TestSuite()
        for t in gen():
            suite_2.addTest(t)

        self.assertEqual(suite_1, suite_2)

    # "Add all the tests from an iterable of TestCase and TestSuite
    # instances to this test suite."
    #
    # What happens if it doesn't get an iterable?
    def test_addTest__noniterable(self):
        suite = unittest2.TestSuite()

        try:
            suite.addTests(5)
        except TypeError:
            pass
        else:
            self.fail("Failed to raise TypeError")

    def test_addTest__noncallable(self):
        suite = unittest2.TestSuite()
        self.assertRaises(TypeError, suite.addTest, 5)

    def test_addTest__casesuiteclass(self):
        suite = unittest2.TestSuite()
        self.assertRaises(TypeError, suite.addTest, Test_TestSuite)
        self.assertRaises(TypeError, suite.addTest, unittest2.TestSuite)

    def test_addTests__string(self):
        suite = unittest2.TestSuite()
        self.assertRaises(TypeError, suite.addTests, "foo")


class Test_FunctionTestCase(unittest2.TestCase):

    # "Return the number of tests represented by the this test object. For
    # unittest2.TestCase instances, this will always be 1"
    def test_countTestCases(self):
        test = unittest2.FunctionTestCase(lambda: None)

        self.assertEqual(test.countTestCases(), 1)

    # "When a setUp() method is defined, the test runner will run that method
    # prior to each test. Likewise, if a tearDown() method is defined, the
    # test runner will invoke that method after each test. In the example,
    # setUp() was used to create a fresh sequence for each test."
    #
    # Make sure the proper call order is maintained, even if setUp() raises
    # an exception.
    def test_run_call_order__error_in_setUp(self):
        events = []
        result = LoggingResult(events)

        def setUp():
            events.append('setUp')
            raise RuntimeError('raised by setUp')

        def test():
            events.append('test')

        def tearDown():
            events.append('tearDown')

        expected = ['startTest', 'setUp', 'addError', 'stopTest']
        unittest2.FunctionTestCase(test, setUp, tearDown).run(result)
        self.assertEqual(events, expected)

    # "When a setUp() method is defined, the test runner will run that method
    # prior to each test. Likewise, if a tearDown() method is defined, the
    # test runner will invoke that method after each test. In the example,
    # setUp() was used to create a fresh sequence for each test."
    #
    # Make sure the proper call order is maintained, even if the test raises
    # an error (as opposed to a failure).
    def test_run_call_order__error_in_test(self):
        events = []
        result = LoggingResult(events)

        def setUp():
            events.append('setUp')

        def test():
            events.append('test')
            raise RuntimeError('raised by test')

        def tearDown():
            events.append('tearDown')

        expected = ['startTest', 'setUp', 'test', 'addError', 'tearDown',
                    'stopTest']
        unittest2.FunctionTestCase(test, setUp, tearDown).run(result)
        self.assertEqual(events, expected)

    # "When a setUp() method is defined, the test runner will run that method
    # prior to each test. Likewise, if a tearDown() method is defined, the
    # test runner will invoke that method after each test. In the example,
    # setUp() was used to create a fresh sequence for each test."
    #
    # Make sure the proper call order is maintained, even if the test signals
    # a failure (as opposed to an error).
    def test_run_call_order__failure_in_test(self):
        events = []
        result = LoggingResult(events)

        def setUp():
            events.append('setUp')

        def test():
            events.append('test')
            self.fail('raised by test')

        def tearDown():
            events.append('tearDown')

        expected = ['startTest', 'setUp', 'test', 'addFailure', 'tearDown',
                    'stopTest']
        unittest2.FunctionTestCase(test, setUp, tearDown).run(result)
        self.assertEqual(events, expected)

    # "When a setUp() method is defined, the test runner will run that method
    # prior to each test. Likewise, if a tearDown() method is defined, the
    # test runner will invoke that method after each test. In the example,
    # setUp() was used to create a fresh sequence for each test."
    #
    # Make sure the proper call order is maintained, even if tearDown() raises
    # an exception.
    def test_run_call_order__error_in_tearDown(self):
        events = []
        result = LoggingResult(events)

        def setUp():
            events.append('setUp')

        def test():
            events.append('test')

        def tearDown():
            events.append('tearDown')
            raise RuntimeError('raised by tearDown')

        expected = ['startTest', 'setUp', 'test', 'tearDown', 'addError',
                    'stopTest']
        unittest2.FunctionTestCase(test, setUp, tearDown).run(result)
        self.assertEqual(events, expected)

    # "Return a string identifying the specific test case."
    #
    # Because of the vague nature of the docs, I'm not going to lock this
    # test down too much. Really all that can be asserted is that the id()
    # will be a string (either 8-byte or unicode -- again, because the docs
    # just say "string")
    def test_id(self):
        test = unittest2.FunctionTestCase(lambda: None)

        self.assertIsInstance(test.id(), basestring)

    # "Returns a one-line description of the test, or None if no description
    # has been provided. The default implementation of this method returns
    # the first line of the test method's docstring, if available, or None."
    def test_shortDescription__no_docstring(self):
        test = unittest2.FunctionTestCase(lambda: None)

        self.assertEqual(test.shortDescription(), None)

    # "Returns a one-line description of the test, or None if no description
    # has been provided. The default implementation of this method returns
    # the first line of the test method's docstring, if available, or None."
    def test_shortDescription__singleline_docstring(self):
        desc = "this tests foo"
        test = unittest2.FunctionTestCase(lambda: None, description=desc)

        self.assertEqual(test.shortDescription(), "this tests foo")

class Test_TestResult(unittest2.TestCase):
    # Note: there are not separate tests for TestResult.wasSuccessful(),
    # TestResult.errors, TestResult.failures, TestResult.testsRun or
    # TestResult.shouldStop because these only have meaning in terms of
    # other TestResult methods.
    #
    # Accordingly, tests for the aforenamed attributes are incorporated
    # in with the tests for the defining methods.
    ################################################################

    def test_init(self):
        result = unittest2.TestResult()

        self.assertTrue(result.wasSuccessful())
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(result.testsRun, 0)
        self.assertEqual(result.shouldStop, False)

    # "This method can be called to signal that the set of tests being
    # run should be aborted by setting the TestResult's shouldStop
    # attribute to True."
    def test_stop(self):
        result = unittest2.TestResult()

        result.stop()

        self.assertEqual(result.shouldStop, True)

    # "Called when the test case test is about to be run. The default
    # implementation simply increments the instance's testsRun counter."
    def test_startTest(self):
        class Foo(unittest2.TestCase):
            def test_1(self):
                pass

        test = Foo('test_1')

        result = unittest2.TestResult()

        result.startTest(test)

        self.assertTrue(result.wasSuccessful())
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(result.shouldStop, False)

        result.stopTest(test)

    # "Called after the test case test has been executed, regardless of
    # the outcome. The default implementation does nothing."
    def test_stopTest(self):
        class Foo(unittest2.TestCase):
            def test_1(self):
                pass

        test = Foo('test_1')

        result = unittest2.TestResult()

        result.startTest(test)

        self.assertTrue(result.wasSuccessful())
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(result.shouldStop, False)

        result.stopTest(test)

        # Same tests as above; make sure nothing has changed
        self.assertTrue(result.wasSuccessful())
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(result.shouldStop, False)

    # "Called before and after tests are run. The default implementation does nothing."
    def test_startTestRun_stopTestRun(self):
        result = unittest2.TestResult()
        result.startTestRun()
        result.stopTestRun()

    # "addSuccess(test)"
    # ...
    # "Called when the test case test succeeds"
    # ...
    # "wasSuccessful() - Returns True if all tests run so far have passed,
    # otherwise returns False"
    # ...
    # "testsRun - The total number of tests run so far."
    # ...
    # "errors - A list containing 2-tuples of TestCase instances and
    # formatted tracebacks. Each tuple represents a test which raised an
    # unexpected exception. Contains formatted
    # tracebacks instead of sys.exc_info() results."
    # ...
    # "failures - A list containing 2-tuples of TestCase instances and
    # formatted tracebacks. Each tuple represents a test where a failure was
    # explicitly signalled using the TestCase.fail*() or TestCase.assert*()
    # methods. Contains formatted tracebacks instead
    # of sys.exc_info() results."
    def test_addSuccess(self):
        class Foo(unittest2.TestCase):
            def test_1(self):
                pass

        test = Foo('test_1')

        result = unittest2.TestResult()

        result.startTest(test)
        result.addSuccess(test)
        result.stopTest(test)

        self.assertTrue(result.wasSuccessful())
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(result.shouldStop, False)

    # "addFailure(test, err)"
    # ...
    # "Called when the test case test signals a failure. err is a tuple of
    # the form returned by sys.exc_info(): (type, value, traceback)"
    # ...
    # "wasSuccessful() - Returns True if all tests run so far have passed,
    # otherwise returns False"
    # ...
    # "testsRun - The total number of tests run so far."
    # ...
    # "errors - A list containing 2-tuples of TestCase instances and
    # formatted tracebacks. Each tuple represents a test which raised an
    # unexpected exception. Contains formatted
    # tracebacks instead of sys.exc_info() results."
    # ...
    # "failures - A list containing 2-tuples of TestCase instances and
    # formatted tracebacks. Each tuple represents a test where a failure was
    # explicitly signalled using the TestCase.fail*() or TestCase.assert*()
    # methods. Contains formatted tracebacks instead
    # of sys.exc_info() results."
    def test_addFailure(self):
        class Foo(unittest2.TestCase):
            def test_1(self):
                pass

        test = Foo('test_1')
        try:
            test.fail("foo")
        except:
            exc_info_tuple = sys.exc_info()

        result = unittest2.TestResult()

        result.startTest(test)
        result.addFailure(test, exc_info_tuple)
        result.stopTest(test)

        self.assertFalse(result.wasSuccessful())
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(result.shouldStop, False)

        test_case, formatted_exc = result.failures[0]
        self.assertTrue(test_case is test)
        self.assertIsInstance(formatted_exc, str)

    # "addError(test, err)"
    # ...
    # "Called when the test case test raises an unexpected exception err
    # is a tuple of the form returned by sys.exc_info():
    # (type, value, traceback)"
    # ...
    # "wasSuccessful() - Returns True if all tests run so far have passed,
    # otherwise returns False"
    # ...
    # "testsRun - The total number of tests run so far."
    # ...
    # "errors - A list containing 2-tuples of TestCase instances and
    # formatted tracebacks. Each tuple represents a test which raised an
    # unexpected exception. Contains formatted
    # tracebacks instead of sys.exc_info() results."
    # ...
    # "failures - A list containing 2-tuples of TestCase instances and
    # formatted tracebacks. Each tuple represents a test where a failure was
    # explicitly signalled using the TestCase.fail*() or TestCase.assert*()
    # methods. Contains formatted tracebacks instead
    # of sys.exc_info() results."
    def test_addError(self):
        class Foo(unittest2.TestCase):
            def test_1(self):
                pass

        test = Foo('test_1')
        try:
            raise TypeError()
        except:
            exc_info_tuple = sys.exc_info()

        result = unittest2.TestResult()

        result.startTest(test)
        result.addError(test, exc_info_tuple)
        result.stopTest(test)

        self.assertFalse(result.wasSuccessful())
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(result.shouldStop, False)

        test_case, formatted_exc = result.errors[0]
        self.assertTrue(test_case is test)
        self.assertIsInstance(formatted_exc, str)

    def testGetDescriptionWithoutDocstring(self):
        result = unittest2.TextTestResult(None, True, 1)
        self.assertEqual(
                result.getDescription(self),
                'testGetDescriptionWithoutDocstring (' + __name__ +
                '.Test_TestResult)')

    def testGetDescriptionWithOneLineDocstring(self):
        """Tests getDescription() for a method with a docstring."""
        result = unittest2.TextTestResult(None, True, 1)
        self.assertEqual(
                result.getDescription(self),
               ('testGetDescriptionWithOneLineDocstring '
                '(' + __name__ + '.Test_TestResult)\n'
                'Tests getDescription() for a method with a docstring.'))

    def testGetDescriptionWithMultiLineDocstring(self):
        """Tests getDescription() for a method with a longer docstring.
        The second line of the docstring.
        """
        result = unittest2.TextTestResult(None, True, 1)
        self.assertEqual(
                result.getDescription(self),
               ('testGetDescriptionWithMultiLineDocstring '
                '(' + __name__ + '.Test_TestResult)\n'
                'Tests getDescription() for a method with a longer '
                'docstring.'))

    def testStackFrameTrimming(self):
        class Frame(object):
            class tb_frame(object):
                f_globals = {}
        result = unittest2.TestResult()
        self.assertFalse(result._is_relevant_tb_level(Frame))
        
        Frame.tb_frame.f_globals['__unittest'] = True
        self.assertTrue(result._is_relevant_tb_level(Frame))

    def testFailFast(self):
        result = unittest2.TestResult()
        result._exc_info_to_string = lambda *_: ''
        result.failfast = True
        result.addError(None, None)
        self.assertTrue(result.shouldStop)

        result = unittest2.TestResult()
        result._exc_info_to_string = lambda *_: ''
        result.failfast = True
        result.addFailure(None, None)
        self.assertTrue(result.shouldStop)

        result = unittest2.TestResult()
        result._exc_info_to_string = lambda *_: ''
        result.failfast = True
        result.addUnexpectedSuccess(None)
        self.assertTrue(result.shouldStop)

    def testFailFastSetByRunner(self):
        runner = unittest2.TextTestRunner(stream=StringIO(), failfast=True)
        def test(result):
            self.assertTrue(result.failfast)
        result = runner.run(test)


### Support code for Test_TestCase
################################################################

class Foo(unittest2.TestCase):
    def runTest(self): pass
    def test1(self): pass

class Bar(Foo):
    def test2(self): pass

def GetLoggingTestCase():
    "Removes LoggingTestCase from module scope."
    class LoggingTestCase(unittest2.TestCase):
        """A test case which logs its calls."""
    
        def __init__(self, events):
            super(LoggingTestCase, self).__init__('test')
            self.events = events
    
        def setUp(self):
            self.events.append('setUp')
    
        def test(self):
            self.events.append('test')
    
        def tearDown(self):
            self.events.append('tearDown')
    return LoggingTestCase

################################################################
### /Support code for Test_TestCase


class Test_TestSkipping(unittest2.TestCase):

    def test_skipping(self):
        class Foo(unittest2.TestCase):
            def test_skip_me(self):
                self.skipTest("skip")
        events = []
        result = LoggingResult(events)
        test = Foo("test_skip_me")
        test.run(result)
        self.assertEqual(events, ['startTest', 'addSkip', 'stopTest'])
        self.assertEqual(result.skipped, [(test, "skip")])

        # Try letting setUp skip the test now.
        class Foo(unittest2.TestCase):
            def setUp(self):
                self.skipTest("testing")
            def test_nothing(self): pass
        events = []
        result = LoggingResult(events)
        test = Foo("test_nothing")
        test.run(result)
        self.assertEqual(events, ['startTest', 'addSkip', 'stopTest'])
        self.assertEqual(result.skipped, [(test, "testing")])
        self.assertEqual(result.testsRun, 1)

    def test_skipping_decorators(self):
        op_table = ((unittest2.skipUnless, False, True),
                    (unittest2.skipIf, True, False))
        for deco, do_skip, dont_skip in op_table:
            class Foo(unittest2.TestCase):
                @deco(do_skip, "testing")
                def test_skip(self): 
                    pass

                @deco(dont_skip, "testing")
                def test_dont_skip(self): 
                    pass
            
            test_do_skip = Foo("test_skip")
            test_dont_skip = Foo("test_dont_skip")
            suite = unittest2.TestSuite([test_do_skip, test_dont_skip])
            events = []
            result = LoggingResult(events)
            suite.run(result)
            self.assertEqual(len(result.skipped), 1)
            expected = ['startTest', 'addSkip', 'stopTest',
                        'startTest', 'addSuccess', 'stopTest']
            self.assertEqual(events, expected)
            self.assertEqual(result.testsRun, 2)
            self.assertEqual(result.skipped, [(test_do_skip, "testing")])
            self.assertTrue(result.wasSuccessful())
        
    def test_skip_class(self):
        class Foo(unittest2.TestCase):
            def test_1(self):
                record.append(1)
        
        # was originally a class decorator...
        Foo = unittest2.skip("testing")(Foo)
        record = []
        result = unittest2.TestResult()
        test = Foo("test_1")
        suite = unittest2.TestSuite([test])
        suite.run(result)
        self.assertEqual(result.skipped, [(test, "testing")])
        self.assertEqual(record, [])

    def test_expected_failure(self):
        class Foo(unittest2.TestCase):
            @unittest2.expectedFailure
            def test_die(self):
                self.fail("help me!")
        events = []
        result = LoggingResult(events)
        test = Foo("test_die")
        test.run(result)
        self.assertEqual(events,
                         ['startTest', 'addExpectedFailure', 'stopTest'])
        self.assertEqual(result.expectedFailures[0][0], test)
        self.assertTrue(result.wasSuccessful())

    def test_unexpected_success(self):
        class Foo(unittest2.TestCase):
            @unittest2.expectedFailure
            def test_die(self):
                pass
        events = []
        result = LoggingResult(events)
        test = Foo("test_die")
        test.run(result)
        self.assertEqual(events,
                         ['startTest', 'addUnexpectedSuccess', 'stopTest'])
        self.assertFalse(result.failures)
        self.assertEqual(result.unexpectedSuccesses, [test])
        self.assertTrue(result.wasSuccessful())

    def test_skip_doesnt_run_setup(self):
        class Foo(unittest2.TestCase):
            wasSetUp = False
            wasTornDown = False
            def setUp(self):
                Foo.wasSetUp = True
            def tornDown(self):
                Foo.wasTornDown = True
            @unittest2.skip('testing')
            def test_1(self):
                pass
        
        result = unittest2.TestResult()
        test = Foo("test_1")
        suite = unittest2.TestSuite([test])
        suite.run(result)
        self.assertEqual(result.skipped, [(test, "testing")])
        self.assertFalse(Foo.wasSetUp)
        self.assertFalse(Foo.wasTornDown)
    
    def test_decorated_skip(self):
        def decorator(func):
            def inner(*a):
                return func(*a)
            return inner
        
        class Foo(unittest2.TestCase):
            @decorator
            @unittest2.skip('testing')
            def test_1(self):
                pass
        
        result = unittest2.TestResult()
        test = Foo("test_1")
        suite = unittest2.TestSuite([test])
        suite.run(result)
        self.assertEqual(result.skipped, [(test, "testing")])


class TestCleanUp(unittest2.TestCase):

    def testCleanUp(self):
        class TestableTest(unittest2.TestCase):
            def testNothing(self):
                pass

        test = TestableTest('testNothing')
        self.assertEqual(test._cleanups, [])

        cleanups = []

        def cleanup1(*args, **kwargs):
            cleanups.append((1, args, kwargs))

        def cleanup2(*args, **kwargs):
            cleanups.append((2, args, kwargs))

        test.addCleanup(cleanup1, 1, 2, 3, four='hello', five='goodbye')
        test.addCleanup(cleanup2)

        self.assertEqual(test._cleanups,
                         [(cleanup1, (1, 2, 3), dict(four='hello', five='goodbye')),
                          (cleanup2, (), {})])

        result = test.doCleanups()
        self.assertTrue(result)

        self.assertEqual(cleanups, [(2, (), {}), (1, (1, 2, 3), dict(four='hello', five='goodbye'))])

    def testCleanUpWithErrors(self):
        class TestableTest(unittest2.TestCase):
            def testNothing(self):
                pass

        class MockResult(object):
            errors = []
            def addError(self, test, exc_info):
                self.errors.append((test, exc_info))

        result = MockResult()
        test = TestableTest('testNothing')
        test._resultForDoCleanups = result

        exc1 = Exception('foo')
        exc2 = Exception('bar')
        def cleanup1():
            raise exc1

        def cleanup2():
            raise exc2

        test.addCleanup(cleanup1)
        test.addCleanup(cleanup2)

        self.assertFalse(test.doCleanups())

        (test1, (Type1, instance1, _)), (test2, (Type2, instance2, _)) = reversed(MockResult.errors)
        self.assertEqual((test1, Type1, instance1), (test, Exception, exc1))
        self.assertEqual((test2, Type2, instance2), (test, Exception, exc2))

    def testCleanupInRun(self):
        blowUp = False
        ordering = []

        class TestableTest(unittest2.TestCase):
            def setUp(self):
                ordering.append('setUp')
                if blowUp:
                    raise Exception('foo')

            def testNothing(self):
                ordering.append('test')

            def tearDown(self):
                ordering.append('tearDown')

        test = TestableTest('testNothing')

        def cleanup1():
            ordering.append('cleanup1')
        def cleanup2():
            ordering.append('cleanup2')
        test.addCleanup(cleanup1)
        test.addCleanup(cleanup2)

        def success(some_test):
            self.assertEqual(some_test, test)
            ordering.append('success')

        result = unittest2.TestResult()
        result.addSuccess = success

        test.run(result)
        self.assertEqual(ordering, ['setUp', 'test', 'tearDown',
                                    'cleanup2', 'cleanup1', 'success'])

        blowUp = True
        ordering = []
        test = TestableTest('testNothing')
        test.addCleanup(cleanup1)
        test.run(result)
        self.assertEqual(ordering, ['setUp', 'cleanup1'])


class Test_TestProgram(unittest2.TestCase):

    # Horrible white box test
    def testNoExit(self):
        result = object()
        test = object()

        class FakeRunner(object):
            def run(self, test):
                self.test = test
                return result

        runner = FakeRunner()

        oldParseArgs = unittest2.TestProgram.parseArgs
        def restoreParseArgs():
            unittest2.TestProgram.parseArgs = oldParseArgs
        unittest2.TestProgram.parseArgs = lambda *args: None
        self.addCleanup(restoreParseArgs)

        def removeTest():
            del unittest2.TestProgram.test
        unittest2.TestProgram.test = test
        self.addCleanup(removeTest)

        program = unittest2.TestProgram(testRunner=runner, exit=False, verbosity=2)

        self.assertEqual(program.result, result)
        self.assertEqual(runner.test, test)
        self.assertEqual(program.verbosity, 2)

    class FooBar(unittest2.TestCase):
        def testPass(self):
            assert True
        def testFail(self):
            assert False

    class FooBarLoader(unittest2.TestLoader):
        """Test loader that returns a suite containing FooBar."""
        def loadTestsFromModule(self, module):
            return self.suiteClass(
                [self.loadTestsFromTestCase(Test_TestProgram.FooBar)])


    def test_NonExit(self):
        program = unittest2.main(exit=False,
                                argv=["foobar"],
                                testRunner=unittest2.TextTestRunner(stream=StringIO()),
                                testLoader=self.FooBarLoader())
        self.assertTrue(hasattr(program, 'result'))


    def test_Exit(self):
        self.assertRaises(
            SystemExit,
            unittest2.main,
            argv=["foobar"],
            testRunner=unittest2.TextTestRunner(stream=StringIO()),
            exit=True,
            testLoader=self.FooBarLoader())


    def test_ExitAsDefault(self):
        self.assertRaises(
            SystemExit,
            unittest2.main,
            argv=["foobar"],
            testRunner=unittest2.TextTestRunner(stream=StringIO()),
            testLoader=self.FooBarLoader())


class Test_TextTestRunner(unittest2.TestCase):
    """Tests for TextTestRunner."""

    def test_works_with_result_without_startTestRun_stopTestRun(self):
        class OldTextResult(OldTestResult):
            def __init__(self, *_):
                super(OldTextResult, self).__init__()
            separator2 = ''
            def printErrors(self):
                pass

        runner = unittest2.TextTestRunner(stream=StringIO(), resultclass=OldTextResult)
        runner.run(unittest2.TestSuite())

    def test_startTestRun_stopTestRun_called(self):
        class LoggingTextResult(LoggingResult):
            separator2 = ''
            def printErrors(self):
                pass

        class LoggingRunner(unittest2.TextTestRunner):
            def __init__(self, events):
                super(LoggingRunner, self).__init__(StringIO())
                self._events = events

            def _makeResult(self):
                return LoggingTextResult(self._events)

        events = []
        runner = LoggingRunner(events)
        runner.run(unittest2.TestSuite())
        expected = ['startTestRun', 'stopTestRun']
        self.assertEqual(events, expected)

    def test_pickle_unpickle(self):
        # Issue #7197: a TextTestRunner should be (un)pickleable. This is
        # required by test_multiprocessing under Windows (in verbose mode).
        import StringIO
        # cStringIO objects are not pickleable, but StringIO objects are.
        stream = StringIO.StringIO("foo")
        runner = unittest2.TextTestRunner(stream)
        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            s = pickle.dumps(runner, protocol=protocol)
            obj = pickle.loads(s)
            # StringIO objects never compare equal, a cheap test instead.
            self.assertEqual(obj.stream.getvalue(), stream.getvalue())

    def test_resultclass(self):
        def MockResultClass(*args):
            return args
        STREAM = object()
        DESCRIPTIONS = object()
        VERBOSITY = object()
        runner = unittest2.TextTestRunner(STREAM, DESCRIPTIONS, VERBOSITY,
                                         resultclass=MockResultClass)
        self.assertEqual(runner.resultclass, MockResultClass)

        expectedresult = (runner.stream, DESCRIPTIONS, VERBOSITY)
        self.assertEqual(runner._makeResult(), expectedresult)
        
    def test_oldresult(self):
        class Test(unittest2.TestCase):
            def testFoo(self):
                pass
        runner = unittest2.TextTestRunner(resultclass=OldTestResult,
                                          stream=StringIO())
        # This will raise an exception if TextTestRunner can't handle old
        # test result objects
        runner.run(Test('testFoo'))

class TestDiscovery(unittest2.TestCase):

    # Heavily mocked tests so I can avoid hitting the filesystem
    def test_get_name_from_path(self):
        loader = unittest2.TestLoader()

        loader._top_level_dir = '/foo'
        name = loader._get_name_from_path('/foo/bar/baz.py')
        self.assertEqual(name, 'bar.baz')

        if not __debug__:
            # asserts are off
            return

        self.assertRaises(AssertionError,
                          loader._get_name_from_path,
                          '/bar/baz.py')

    def test_find_tests(self):
        loader = unittest2.TestLoader()

        original_listdir = os.listdir
        def restore_listdir():
            os.listdir = original_listdir
        original_isfile = os.path.isfile
        def restore_isfile():
            os.path.isfile = original_isfile
        original_isdir = os.path.isdir
        def restore_isdir():
            os.path.isdir = original_isdir

        path_lists = [['test1.py', 'test2.py', 'not_a_test.py', 'test_dir',
                       'test.foo', 'test-not-a-module.py', 'another_dir'],
                      ['test3.py', 'test4.py', ]]
        os.listdir = lambda path: path_lists.pop(0)
        self.addCleanup(restore_listdir)

        def isdir(path):
            return path.endswith('dir')
        os.path.isdir = isdir
        self.addCleanup(restore_isdir)

        def isfile(path):
            # another_dir is not a package and so shouldn't be recursed into
            return not path.endswith('dir') and not 'another_dir' in path
        os.path.isfile = isfile
        self.addCleanup(restore_isfile)

        loader._get_module_from_name = lambda path: path + ' module'
        loader.loadTestsFromModule = lambda module: module + ' tests'

        loader._top_level_dir = '/foo'
        suite = list(loader._find_tests('/foo', 'test*.py'))

        expected = [name + ' module tests' for name in
                    ('test1', 'test2')]
        expected.extend([('test_dir.%s' % name) + ' module tests' for name in
                    ('test3', 'test4')])
        self.assertEqual(suite, expected)

    def test_find_tests_with_package(self):
        loader = unittest2.TestLoader()

        original_listdir = os.listdir
        def restore_listdir():
            os.listdir = original_listdir
        original_isfile = os.path.isfile
        def restore_isfile():
            os.path.isfile = original_isfile
        original_isdir = os.path.isdir
        def restore_isdir():
            os.path.isdir = original_isdir

        directories = ['a_directory', 'test_directory', 'test_directory2']
        path_lists = [directories, [], [], []]
        os.listdir = lambda path: path_lists.pop(0)
        self.addCleanup(restore_listdir)

        os.path.isdir = lambda path: True
        self.addCleanup(restore_isdir)

        os.path.isfile = lambda path: os.path.basename(path) not in directories
        self.addCleanup(restore_isfile)

        class Module(object):
            paths = []
            load_tests_args = []

            def __init__(self, path):
                self.path = path
                self.paths.append(path)
                if os.path.basename(path) == 'test_directory':
                    def load_tests(loader, tests, pattern):
                        self.load_tests_args.append((loader, tests, pattern))
                        return 'load_tests'
                    self.load_tests = load_tests

            def __eq__(self, other):
                return self.path == other.path

            # Silence py3k warning
            __hash__ = None

        loader._get_module_from_name = lambda name: Module(name)
        def loadTestsFromModule(module, use_load_tests):
            if use_load_tests:
                raise self.failureException('use_load_tests should be False for packages')
            return module.path + ' module tests'
        loader.loadTestsFromModule = loadTestsFromModule

        loader._top_level_dir = '/foo'
        # this time no '.py' on the pattern so that it can match
        # a test package
        suite = list(loader._find_tests('/foo', 'test*'))

        # We should have loaded tests from the test_directory package by calling load_tests
        # and directly from the test_directory2 package
        self.assertEqual(suite,
                         ['load_tests', 'test_directory2' + ' module tests'])
        self.assertEqual(Module.paths, ['test_directory', 'test_directory2'])

        # load_tests should have been called once with loader, tests and pattern
        self.assertEqual(Module.load_tests_args,
                         [(loader, 'test_directory' + ' module tests', 'test*')])

    def test_discover(self):
        loader = unittest2.TestLoader()

        original_isfile = os.path.isfile
        def restore_isfile():
            os.path.isfile = original_isfile

        os.path.isfile = lambda path: False
        self.addCleanup(restore_isfile)

        orig_sys_path = sys.path[:]
        def restore_path():
            sys.path[:] = orig_sys_path
        self.addCleanup(restore_path)

        full_path = os.path.abspath(os.path.normpath('/foo'))
        self.assertRaises(ImportError,
                          loader.discover,
                          '/foo/bar', top_level_dir='/foo')

        self.assertEqual(loader._top_level_dir, full_path)
        self.assertIn(full_path, sys.path)

        os.path.isfile = lambda path: True
        _find_tests_args = []
        def _find_tests(start_dir, pattern):
            _find_tests_args.append((start_dir, pattern))
            return ['tests']
        loader._find_tests = _find_tests
        loader.suiteClass = str

        suite = loader.discover('/foo/bar/baz', 'pattern', '/foo/bar')

        top_level_dir = os.path.abspath(os.path.normpath('/foo/bar'))
        start_dir = os.path.abspath(os.path.normpath('/foo/bar/baz'))
        self.assertEqual(suite, "['tests']")
        self.assertEqual(loader._top_level_dir, top_level_dir)
        self.assertEqual(_find_tests_args, [(start_dir, 'pattern')])
        self.assertIn(top_level_dir, sys.path)

    def test_discover_with_modules_that_fail_to_import(self):
        loader = unittest2.TestLoader()

        listdir = os.listdir
        os.listdir = lambda _: ['test_this_does_not_exist.py']
        isfile = os.path.isfile
        os.path.isfile = lambda _: True
        orig_sys_path = sys.path[:]
        def restore():
            os.path.isfile = isfile
            os.listdir = listdir
            sys.path[:] = orig_sys_path
        self.addCleanup(restore)

        suite = loader.discover('.')
        self.assertIn(os.getcwd(), sys.path)
        self.assertEqual(suite.countTestCases(), 1)
        test = list(list(suite)[0])[0] # extract test from suite

        self.assertRaises(ImportError,
            lambda: test.test_this_does_not_exist())

    def test_command_line_handling_parseArgs(self):
        # Haha - take that uninstantiable class
        program = object.__new__(unittest2.TestProgram)

        args = []
        def do_discovery(argv):
            args.extend(argv)
        program._do_discovery = do_discovery
        program.parseArgs(['something', 'discover'])
        self.assertEqual(args, [])

        program.parseArgs(['something', 'discover', 'foo', 'bar'])
        self.assertEqual(args, ['foo', 'bar'])

    def test_command_line_handling_do_discovery_too_many_arguments(self):
        class Stop(Exception):
            pass
        def usageExit():
            raise Stop

        program = object.__new__(unittest2.TestProgram)
        program.usageExit = usageExit

        self.assertRaises(Stop,
            # too many args
            lambda: program._do_discovery(['one', 'two', 'three', 'four']))


    def test_command_line_handling_do_discovery_calls_loader(self):
        program = object.__new__(unittest2.TestProgram)

        class Loader(object):
            args = []
            def discover(self, start_dir, pattern, top_level_dir):
                self.args.append((start_dir, pattern, top_level_dir))
                return 'tests'

        program._do_discovery(['-v'], Loader=Loader)
        self.assertEqual(program.verbosity, 2)
        self.assertEqual(program.test, 'tests')
        self.assertEqual(Loader.args, [('.', 'test*.py', None)])

        Loader.args = []
        program = object.__new__(unittest2.TestProgram)
        program._do_discovery(['--verbose'], Loader=Loader)
        self.assertEqual(program.test, 'tests')
        self.assertEqual(Loader.args, [('.', 'test*.py', None)])

        Loader.args = []
        program = object.__new__(unittest2.TestProgram)
        program._do_discovery([], Loader=Loader)
        self.assertEqual(program.test, 'tests')
        self.assertEqual(Loader.args, [('.', 'test*.py', None)])

        Loader.args = []
        program = object.__new__(unittest2.TestProgram)
        program._do_discovery(['fish'], Loader=Loader)
        self.assertEqual(program.test, 'tests')
        self.assertEqual(Loader.args, [('fish', 'test*.py', None)])

        Loader.args = []
        program = object.__new__(unittest2.TestProgram)
        program._do_discovery(['fish', 'eggs'], Loader=Loader)
        self.assertEqual(program.test, 'tests')
        self.assertEqual(Loader.args, [('fish', 'eggs', None)])

        Loader.args = []
        program = object.__new__(unittest2.TestProgram)
        program._do_discovery(['fish', 'eggs', 'ham'], Loader=Loader)
        self.assertEqual(program.test, 'tests')
        self.assertEqual(Loader.args, [('fish', 'eggs', 'ham')])

        Loader.args = []
        program = object.__new__(unittest2.TestProgram)
        program._do_discovery(['-s', 'fish'], Loader=Loader)
        self.assertEqual(program.test, 'tests')
        self.assertEqual(Loader.args, [('fish', 'test*.py', None)])

        Loader.args = []
        program = object.__new__(unittest2.TestProgram)
        program._do_discovery(['-t', 'fish'], Loader=Loader)
        self.assertEqual(program.test, 'tests')
        self.assertEqual(Loader.args, [('.', 'test*.py', 'fish')])

        Loader.args = []
        program = object.__new__(unittest2.TestProgram)
        program._do_discovery(['-p', 'fish'], Loader=Loader)
        self.assertEqual(program.test, 'tests')
        self.assertEqual(Loader.args, [('.', 'fish', None)])
        self.assertFalse(program.failfast)
        self.assertFalse(program.catchbreak)

        Loader.args = []
        program = object.__new__(unittest2.TestProgram)
        program._do_discovery(['-p', 'eggs', '-s', 'fish', '-v', '-f', '-c'], 
                              Loader=Loader)
        self.assertEqual(program.test, 'tests')
        self.assertEqual(Loader.args, [('fish', 'eggs', None)])
        self.assertEqual(program.verbosity, 2)
        self.assertTrue(program.failfast)
        self.assertTrue(program.catchbreak)


if __name__ == "__main__":
    unittest2.main()