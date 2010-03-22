import os
import signal

import unittest2

from cStringIO import StringIO


@unittest2.skipUnless(hasattr(os, 'kill'), "test uses os.kill(...)")
class TestBreak(unittest2.TestCase):

    def testInterruptCaught(self):
        default_handler = signal.getsignal(signal.SIGINT)
        
        result = unittest2.TestResult()
        unittest2.util.install_handler(result)
        
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
        
        