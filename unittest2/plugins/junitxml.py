from unittest2.events import Plugin, addOption


class JunitXml(Plugin):
    
    configSection = 'junit-xml'
    commandLineSwitch = ('J', 'junit-xml', 'Generate junit-xml output report')
    
    def __init__(self):
        self.path = self.config.as_bool('path', default='junit.xml')

    def startTest(self, event):
        pass

    def stopTest(self, event):
        pass

    def stopTestRun(self, event):
        # probably not valid xml
        open(self.path, 'w').write('foo')
