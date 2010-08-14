from unittest2 import Plugin, addOption, TestSuite

import re

def flatten(thing):
    try:
        for sub_thing in thing:
            for test in flatten(sub_thing):
                yield test
    except TypeError:
        yield thing

class FilterTests(Plugin):
    """
    Filter which test methods on TestCase classes
    are loaded, using a regular expression.
    """
    def __init__(self):
        self.regex = []
        help_text = 'Filter test methods loaded with a regexp'
        addOption(self.regex, 'F', 'filter', help_text)
        self.register()

    def pluginsLoaded(self, event):
        self.regex = [re.compile(regex) for regex in self.regex]
        if not self.regex:
            self.unregister()

    def startTestRun(self, event):
        suite = TestSuite()
        regexes = self.regex
        for test in flatten(event.suite):
            try:
                name = test.id()
            except AttributeError:
                name = test.__name__
            
            for regex in regexes:
                if regex.search(name):
                    suite.addTest(test)
                    break
        event.suite = suite
