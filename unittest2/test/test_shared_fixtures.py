import sys

from cStringIO import StringIO

import unittest2
from unittest2.test.support import OldTestResult

def resultFactory(*_):
    return unittest2.TestResult()

class TestSetups(unittest2.TestCase):

    def runTests(self, *cases):
        suite = unittest2.TestSuite()
        for case in cases:
            tests = unittest2.defaultTestLoader.loadTestsFromTestCase(case)
            suite.addTests(tests)
        runner = unittest2.TextTestRunner(resultclass=resultFactory,
                                          stream=StringIO())
        
        # creating a nested suite exposes some potential bugs
        realSuite = unittest2.TestSuite()
        realSuite.addTest(suite)
        # adding empty suites to the end exposes potential bugs
        suite.addTest(unittest2.TestSuite())
        realSuite.addTest(unittest2.TestSuite())
        return runner.run(realSuite)

    def test_setup_class(self):
        class Test(unittest2.TestCase):
            setUpCalled = 0
            @classmethod
            def setUpClass(cls):
                Test.setUpCalled += 1
                unittest2.TestCase.setUpClass()
            def test_one(self):
                pass
            def test_two(self):
                pass
            
        result = self.runTests(Test)
        
        self.assertEqual(Test.setUpCalled, 1)
        self.assertEqual(result.testsRun, 2)
        self.assertEqual(len(result.errors), 0)

    def test_teardown_class(self):
        class Test(unittest2.TestCase):
            tearDownCalled = 0
            @classmethod
            def tearDownClass(cls):
                Test.tearDownCalled += 1
                unittest2.TestCase.tearDownClass()
            def test_one(self):
                pass
            def test_two(self):
                pass
            
        result = self.runTests(Test)
        
        self.assertEqual(Test.tearDownCalled, 1)
        self.assertEqual(result.testsRun, 2)
        self.assertEqual(len(result.errors), 0)
    
    def test_teardown_class_two_classes(self):
        class Test(unittest2.TestCase):
            tearDownCalled = 0
            @classmethod
            def tearDownClass(cls):
                Test.tearDownCalled += 1
                unittest2.TestCase.tearDownClass()
            def test_one(self):
                pass
            def test_two(self):
                pass
            
        class Test2(unittest2.TestCase):
            tearDownCalled = 0
            @classmethod
            def tearDownClass(cls):
                Test2.tearDownCalled += 1
                unittest2.TestCase.tearDownClass()
            def test_one(self):
                pass
            def test_two(self):
                pass
        
        result = self.runTests(Test, Test2)
        
        self.assertEqual(Test.tearDownCalled, 1)
        self.assertEqual(Test2.tearDownCalled, 1)
        self.assertEqual(result.testsRun, 4)
        self.assertEqual(len(result.errors), 0)

    def test_error_in_setupclass(self):
        class BrokenTest(unittest2.TestCase):
            @classmethod
            def setUpClass(cls):
                raise TypeError('foo')
            def test_one(self):
                pass
            def test_two(self):
                pass
        
        result = self.runTests(BrokenTest)
        
        self.assertEqual(result.testsRun, 0)
        self.assertEqual(len(result.errors), 1)
        error, _ = result.errors[0]
        self.assertEqual(str(error), 
                    'classSetUp (unittest2.test.test_shared_fixtures.BrokenTest)')

    def test_error_in_teardown_class(self):
        class Test(unittest2.TestCase):
            tornDown = 0
            @classmethod
            def tearDownClass(cls):
                Test.tornDown += 1
                raise TypeError('foo')
            def test_one(self):
                pass
            def test_two(self):
                pass
            
        class Test2(unittest2.TestCase):
            tornDown = 0
            @classmethod
            def tearDownClass(cls):
                Test2.tornDown += 1
                raise TypeError('foo')
            def test_one(self):
                pass
            def test_two(self):
                pass
        
        result = self.runTests(Test, Test2)
        self.assertEqual(result.testsRun, 4)
        self.assertEqual(len(result.errors), 2)
        self.assertEqual(Test.tornDown, 1)
        self.assertEqual(Test2.tornDown, 1)
        
        error, _ = result.errors[0]
        self.assertEqual(str(error), 
                    'classTearDown (unittest2.test.test_shared_fixtures.Test)')

    def test_class_not_torndown_when_setup_fails(self):
        class Test(unittest2.TestCase):
            tornDown = False
            @classmethod
            def setUpClass(cls):
                raise TypeError
            @classmethod
            def tearDownClass(cls):
                Test.tornDown = True
                raise TypeError('foo')
            def test_one(self):
                pass

        self.runTests(Test)
        self.assertFalse(Test.tornDown)
    
    def test_class_not_setup_when_skipped(self):
        class Test(unittest2.TestCase):
            classSetUp = False
            @classmethod
            def setUpClass(cls):
                Test.classSetUp = True
            def test_one(self):
                pass

        Test = unittest2.skip("hop")(Test)
        self.runTests(Test)
        self.assertFalse(Test.classSetUp)
        
            
    def test_setup_module(self):
        class Module(object):
            moduleSetup = 0
            @staticmethod
            def setUpModule():
                Module.moduleSetup += 1
        
        class Test(unittest2.TestCase):
            def test_one(self):
                pass
            def test_two(self):
                pass
        Test.__module__ = 'Module'
        sys.modules['Module'] = Module
        
        result = self.runTests(Test)
        self.assertEqual(Module.moduleSetup, 1)
        self.assertEqual(result.testsRun, 2)
        self.assertEqual(len(result.errors), 0)
    
    def test_error_in_setup_module(self):
        class Module(object):
            moduleSetup = 0
            @staticmethod
            def setUpModule():
                Module.moduleSetup += 1
                raise TypeError('foo')
        
        class Test(unittest2.TestCase):
            classSetUp = False
            classTornDown = False
            @classmethod
            def setUpClass(cls):
                Test.classSetUp = True
            @classmethod
            def tearDownClass(cls):
                Test.classTornDown = True
            def test_one(self):
                pass
            def test_two(self):
                pass
        
        class Test2(unittest2.TestCase):
            def test_one(self):
                pass
            def test_two(self):
                pass
        Test.__module__ = 'Module'
        Test2.__module__ = 'Module'
        sys.modules['Module'] = Module
        
        result = self.runTests(Test, Test2)
        self.assertEqual(Module.moduleSetup, 1)
        self.assertEqual(result.testsRun, 0)
        self.assertFalse(Test.classSetUp)
        self.assertFalse(Test.classTornDown)
        self.assertEqual(len(result.errors), 1)
        error, _ = result.errors[0]
        self.assertEqual(str(error), 'moduleSetUp (Module)')
        
    def test_setup_module_with_missing_module(self):
        class Module(object):
            moduleSetup = 0
            @staticmethod
            def setUpModule():
                Module.moduleSetup += 1
                raise TypeError('foo')
        
        class Test(unittest2.TestCase):
            def test_one(self):
                pass
            def test_two(self):
                pass
        Test.__module__ = 'Module'
        if 'Module' in sys.modules:
            del sys.modules['Module']
        
        result = self.runTests(Test)
        self.assertEqual(Module.moduleSetup, 0)
        self.assertEqual(result.testsRun, 2)
        
    # XXXX not implemented yet
    @unittest2.expectedFailure
    def test_teardown_module(self):
        class Module(object):
            moduleTornDown = 0
            @staticmethod
            def tearDownModule():
                Module.moduleTornDown += 1
        
        class Test(unittest2.TestCase):
            def test_one(self):
                pass
            def test_two(self):
                pass
        Test.__module__ = 'Module'
        sys.modules['Module'] = Module
        
        result = self.runTests(Test)
        self.assertEqual(Module.moduleTornDown, 1)
        self.assertEqual(result.testsRun, 2)
        self.assertEqual(len(result.errors), 0)

"""
Not tested yet.

setUpClass should not be run for skipped classes.

For unittest2 - TestCase without setUpClass should not die.

tearDownModule should not die when modules not in sys.modules.

Meaning of SkipTest in setUpClass - skip whole class.
SkipTest in setUpModule should skip whole module.


To document:
    setUpClass failure means that tests in that class will *not* be run
    and reported.
    
    TestSuite.debug now has very different semantics from TestSuite.run().
    It does not run the shared fixture code.

"""
