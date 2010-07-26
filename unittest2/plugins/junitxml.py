"""
An example plugin that generates junit compatible xml test reports. Useful
for continuous integration with hudson and other tools.

Code for this plugin mainly derived from the py.test junit plugin:
    http://codespeak.net/py/dist/test/plugin/junitxml.html

"""

from unittest2.events import Plugin, addOption

def xmlEscape(value):
    return value

class JunitXml(Plugin):
    
    configSection = 'junit-xml'
    commandLineSwitch = ('J', 'junit-xml', 'Generate junit-xml output report')
    
    def __init__(self):
        self.path = self.config.as_bool('path', default='junit.xml')
        self.errors = 0
        self.failed = 0
        self.skipped = 0
        self.numtests = 0
        self.test_logs = []

    def startTest(self, event):
        self.numtests += 1

    def stopTest(self, event):
        d = {'time': "%.6f" % event.timeTaken}
        test = event.test
        classnames = ('%s.%s' % (test.__module__, 
                                 test.__class__.__name__)).split('.')
        d['classname'] = ".".join(classnames)
        d['name'] = xmlEscape(test._testMethodName)
        attrs = ['%s="%s"' % item for item in sorted(d.items())]
        
        self.test_logs.append('<testcase %s>' % ' '.join(attrs))
        
        msg = ''
        if event.exc_info:
            msg = xmlEscape(event.exc_info[1])
        if event.error:
            self.errors += 1
            self.test_logs.append(
                '<error message="test failure">%s</error>' % msg
            )
        elif event.failed:
            self.failed += 1
            self.test_logs.append(
                '<failure message="test failure">%s</failure>' % msg
            )
        elif event.unexpectedSuccess:
            self.skipped += 1
            self.test_logs.append(
                '<skipped message="test passes unexpectedly"/>'
            )
        elif event.skipped:
            self.skipped += 1
            self.test_logs.append("<skipped/>")
        elif event.expectedFailure:
            self.skipped += 1
            self.test_logs.append(
                '<skipped message="expected test failure">%s</skipped>' % msg
            )
        
        self.test_logs.append("</testcase>")
        

    def stopTestRun(self, event):
        data = []
        data.append('<?xml version="1.0" encoding="utf-8"?>')
        data.append('<testsuite ')
        data.append('name="" ')
        data.append('errors="%i" ' % self.errors)
        data.append('failures="%i" ' % self.failed)
        data.append('skips="%i" ' % self.skipped)
        data.append('tests="%i" ' % self.numtests)
        data.append('time="%.3f"' % event.timeTaken)
        data.append(' >')
        data.extend(self.test_logs)
        data.append('</testsuite>')
        
        handle = open(self.path, 'w')
        try:
            handle.write('\n'.join(data))
            handle.write('\n')
        finally:
            handle.close()
