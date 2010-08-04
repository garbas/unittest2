"""
An example plugin that generates junit compatible xml test reports. Useful
for continuous integration with hudson and other tools.

Code for this plugin mainly derived from the py.test junit plugin:
    http://codespeak.net/py/dist/test/plugin/junitxml.html

"""

from xml.etree import ElementTree as ET

from unittest2.events import Plugin, addOption

class JunitXml(Plugin):

    configSection = 'junit-xml'
    commandLineSwitch = ('X', 'junit-xml', 'Generate junit-xml output report')

    def __init__(self):
        self.path = self.config.as_str('path', default='junit.xml')
        self.errors = 0
        self.failed = 0
        self.skipped = 0
        self.numtests = 0
        self.tree = ET.Element('testsuite')

    def startTest(self, event):
        self.numtests += 1

    def stopTest(self, event):
        test = event.test
        classnames = ('%s.%s' % (test.__module__,
                                 test.__class__.__name__)).split('.')
        testcase = ET.SubElement(self.tree, 'testcase')
        testcase.set('time', "%.6f" % event.timeTaken)
        testcase.set('classname', '.'.join(classnames))
        testcase.set('name', test._testMethodName)

        msg = ''
        if event.exc_info:
            msg = xmlEscape(event.exc_info[1])
        if event.error:
            self.errors += 1
            error = ET.SubElement(testcase, 'error')
            error.set('message', 'test failure')
            error.text = msg
        elif event.failed:
            self.failed += 1
            failure = ET.SubElement(testcase, 'failure')
            failure.set('message', 'test failure')
            failure.text = msg
        elif event.unexpectedSuccess:
            self.skipped += 1
            skipped = ET.SubElement(testcase, 'skipped')
            skipped.set('message', 'test passes unexpectedly')
        elif event.skipped:
            self.skipped += 1
            skipped = ET.SubElement(testcase, 'skipped')
            # XXX Unfinished?
            self.test_logs.append("<skipped/>")
        elif event.expectedFailure:
            self.skipped += 1
            skipped = ET.SubElement(testcase, 'skipped')
            skipped.set('message', 'expected test failure')
            skipped.text = msg

    def stopTestRun(self, event):
        self.tree.set('name', 'w00t')
        self.tree.set('errors', str(self.errors))
        self.tree.set('failures' , str(self.failed))
        self.tree.set('skips', str(self.skipped))
        self.tree.set('tests', str(self.numtests))
        self.tree.set('time', "%.3f" % event.timeTaken)

        self._indent_tree(self.tree)
        output = ET.ElementTree(self.tree)
        output.write(self.path, encoding="utf-8", xml_declaration=True)

    def _indent_tree(self, elem, level=0):
        """In-place pretty formatting of the ElementTree structure."""
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self._indent_tree(elem, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
