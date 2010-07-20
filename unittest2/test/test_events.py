import unittest2

from collections import deque

class TestEvents(unittest2.TestCase):
    
    def test_eventhook(self):
        hook = unittest2.events._EventHook()
        self.assertEqual(hook._handlers, deque())
        
        self.called = False
        event = object()
        return_val = False
        def handler1(arg):
            self.assertIs(arg, event)
            self.called = True
            return return_val
        
        hook += handler1
        result = hook(event)
        self.assertFalse(result)
        self.assertTrue(self.called)
        
        self.called = False
        def handler2(arg):
            self.assertIs(arg, event)
            return return_val
        hook += handler2
        
        result = hook(event)
        self.assertFalse(result)
        self.assertTrue(self.called)
        
        self.called = False
        return_val = object()
        result = hook(event)
        self.assertIs(result, return_val)
        self.assertFalse(self.called)
        
        hook -= handler1
        hook -= handler2
        hook(object())
        self.assertEqual(hook._handlers, deque())


if __name__ == '__main__':
    unittest2.main()