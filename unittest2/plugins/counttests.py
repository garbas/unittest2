from unittest2 import Plugin

class CountTests(Plugin):
    
    configSection = 'count'
    commandLineSwitch = (None, 'count', "display a progress indicator of tests")

    def startTestRun(self, event):
        self.current = 0
        self.totalTests = event.suite.countTestCases()
    
    def startTest(self, event):
        self.current += 1
        msg = '[%s/%s]  ' % (self.current, self.totalTests)
        event.message(msg, "verbose")
