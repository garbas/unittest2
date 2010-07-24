from unittest2.events import Plugin, addOption, loadConfig

import re

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
    
    def getTestCaseNames(self, event):
        testCase = event.testCase
        
        def is_invalid(attr):
            for regex in self.regex:
                if regex.match(attr):
                    return False
            return True
        
        excluded = filter(is_invalid, dir(testCase))
        event.excludedNames.extend(excluded)