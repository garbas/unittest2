from unittest2.events import Plugin

import time

help_text = 'Output time taken for each test (verbose only)'

class TimedTests(Plugin):
    
    configSection = 'timed'
    commandLineSwitch = ('T', 'timed', help_text)

    def __init__(self):
        self.threshold = self.config.as_float('threshold', 0)

    def stopTest(self, event):
        if event.timeTaken >= self.threshold:
            msg = '  %.2f seconds  ' % event.timeTaken
            # only output in verbose (verbosity = 2)
            event.message(msg, 2)
