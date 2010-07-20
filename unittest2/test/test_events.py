import os
import unittest2


class TestEvents(unittest2.TestCase):
    
    def test_eventhook(self):
        hook = unittest2.events._EventHook()
        self.assertEqual(hook._handlers, [])
        
        self.called = False
        event = unittest2.events._Event()
        return_val = False
        def handler1(arg):
            self.assertIs(arg, event)
            self.called = True
            arg.handled = bool(return_val)
            return return_val
        
        hook += handler1
        result = hook(event)
        self.assertFalse(result)
        self.assertTrue(self.called)
        
        self.called = False
        def handler2(arg):
            self.assertIs(arg, event)
            arg.handled = bool(return_val)
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
        self.assertEqual(hook._handlers, [])

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
    
    def test_loader_uses_handlefileevent(self):
        loader = unittest2.TestLoader()
        top_level = object()
        loader._top_level_dir = top_level
        
        suite = object()
        def handler(event):
            self.assertIsInstance(event, unittest2.events.HandleFileEvent)
            self.event = event
            event.handled = True
            return suite
        
        def fake_listdir(_):
            return ['foo']
        def fake_isfile(_):
            return True
        original_listdir = os.listdir
        original_isfile = os.path.isfile
        self.event = None
        def restore():
            unittest2.events.events.handleFile -= handler
            os.listdir = original_listdir
            os.path.isfile = original_isfile
        unittest2.events.events.handleFile += handler
        os.listdir = fake_listdir
        os.path.isfile = fake_isfile
        self.addCleanup(restore)
    
        tests = list(loader._find_tests('start', 'pattern'))
        
        self.assertIsNotNone(self.event)
        self.assertEqual(tests, [suite])
        
        event = self.event
        self.assertIs(event.loader, loader)
        self.assertEqual(event.name, 'foo')
        self.assertEqual(event.path, os.path.join('start', 'foo'))
        self.assertEqual(event.pattern, 'pattern')
        self.assertEqual(event.top_level_directory, top_level)

if __name__ == '__main__':
    unittest2.main()