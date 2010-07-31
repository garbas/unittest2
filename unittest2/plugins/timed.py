from unittest2.events import Plugin

import time

class TimedTests(Plugin):
    
    configSection = 'timed'
    commandLineSwitch = ('T', 'timed', 'Output time taken for each test')

    def __init__(self):
        self.threshold = self.config.as_float('threshold', 0)

    def stopTest(self, event):
        if event.timeTaken >= self.threshold:
            msg = '  %.2f seconds  ' % event.timeTaken
            event.message(msg, 2)
