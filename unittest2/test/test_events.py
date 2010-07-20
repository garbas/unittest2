import unittest2


class TestEvents(unittest2.TestCase):
    
    def test_eventhook(self):
        hook = unittest2.events._EventHook()
        self.assertEqual(hook._handlers, [])
        
        self.called = False
        event = object()
        return_val = False
        def handler1(arg):
            self.assertIs(arg, event)
            self.called = True
            return return_val
        
        hook += handler1
        hook(event)
        self.assertTrue(self.called)
        
        self.called = False
        def handler2(arg):
            self.assertIs(arg, event)
            return return_val
        hook(event)
        self.assertTrue(self.called)
        
        self.called = False
        return_val = True
        hook(event)
        self.assertFalse(self.called)
        
        hook -= handler1
        hook -= handler2
        hook(object())
        self.assertEqual(hook._handlers, [])


if __name__ == '__main__':
    unittest2.main()