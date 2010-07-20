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

    def test_handlefileevent(self):
        loader = object()
        path = object()
        name = object()
        pattern = object()
        top_level_directory = object()
        event = unittest2.events.HandleFileEvent(loader, name, path, pattern,
                                                  top_level_directory)
        
        self.assertIs(event.loader, loader)
        self.assertIs(event.path, path)
        self.assertIs(event.name, name)
        self.assertIs(event.pattern, pattern)
        

if __name__ == '__main__':
    unittest2.main()