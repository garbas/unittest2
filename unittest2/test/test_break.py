import os
import signal

import unittest2

from cStringIO import StringIO


class TestBreak(unittest2.TestCase):
    
    def setUp(self):
        self._default_handler = signal.getsignal(signal.SIGINT)
        
    def tearDown(self):
        signal.signal(signal.SIGINT, self._default_handler)
        unittest2.util._results = set()
        unittest2.util._interrupt_handler = None

    def testInterruptCaught(self):
        default_handler = signal.getsignal(signal.SIGINT)
        
        result = unittest2.TestResult()
        unittest2.install_handler(result)
        
        self.assertNotEqual(signal.getsignal(signal.SIGINT), default_handler)
        
        def test(result):
            pid = os.getpid()
            os.kill(pid, signal.SIGINT)
            result.breakCaught = True
            self.assertTrue(result.shouldStop)
        
        try:
            test(result)
        except KeyboardInterrupt:
            self.fail("KeyboardInterrupt not handled")
        self.assertTrue(result.breakCaught)
    
    
    def testSecondInterrupt(self):
        result = unittest2.TestResult()
        unittest2.install_handler(result)
        
        def test(result):
            pid = os.getpid()
            os.kill(pid, signal.SIGINT)
            result.breakCaught = True
            self.assertTrue(result.shouldStop)
            os.kill(pid, signal.SIGINT)
            self.fail("Second KeyboardInterrupt not raised")
        
        try:
            test(result)
        except KeyboardInterrupt:
            pass
        else:
            self.fail("Second KeyboardInterrupt not raised")
        self.assertTrue(result.breakCaught)

    
    def testTwoResults(self):
        result = unittest2.TestResult()
        unittest2.install_handler(result)
        new_handler = signal.getsignal(signal.SIGINT)
        
        result2 = unittest2.TestResult()
        unittest2.install_handler(result2)
        self.assertEqual(signal.getsignal(signal.SIGINT), new_handler)
        
        def test(result):
            pid = os.getpid()
            os.kill(pid, signal.SIGINT)
        
        try:
            test(result)
        except KeyboardInterrupt:
            self.fail("KeyboardInterrupt not handled")
        
        self.assertTrue(result.shouldStop)
        self.assertTrue(result2.shouldStop)
    
    
    def testHandlerReplacedButCalled(self):
        # If our handler has been replaced (is no longer installed) but is
        # called by the *new* handler, then it isn't safe to delay the
        # SIGINT and we should immediately delegate to the default handler
        self.fail('not done yet')
        
    
    def testWeakReferences(self):
        # Calling install_handler on a result should not keep it alive
        self.fail('not done yet')
    
    def testRemoveHandler(self):
        # need an API for de-registering result objects
        self.fail('not done yet')
    
    def testRemoveLastHandler(self):
        # (Optional?) De-registering the last result should re-install the
        # default handler
        self.fail('not done yet')
    
    def testRunner(self):
        # Creating a TextTestRunner with the appropriate argument should
        # register the TextTestResult it creates
        self.fail('not done yet')
    
    def testCommandLine(self):
        # The appropriate command line flags (or argument to main?) should
        # create the runner with the right argument
        self.fail('not done yet')
        
        # note also that main may not have a failfast parameter yet

skipper = unittest2.skipUnless(hasattr(os, 'kill'), "test uses os.kill(...)")
TestBreak = skipper(TestBreak)
