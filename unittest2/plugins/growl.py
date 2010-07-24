"""
Example unittest plugin.

Requires py-Growl.

Code liberally "borrowed" from NoseGrowl:
    http://bitbucket.org/crankycoder/nosegrowl/
    
This plugin is licensed under GNU LGPL (inherited from nosegrowl).
"""
from unittest2.events import Plugin, addOption, getConfig

import warnings
# py-Growl uses md5
warnings.filterwarnings("ignore", category=DeprecationWarning)

import datetime

try:
    from Growl import GrowlNotifier, GROWL_NOTIFICATIONS_DEFAULT
except ImportError, e:
    GrowlNotifier = None
    growlImportError = e
    
class SimpleNotifier(object):
    def __init__(self, app_name='unittest2'):
        self.growl = GrowlNotifier(
            applicationName=app_name,
            notifications=[GROWL_NOTIFICATIONS_DEFAULT]
        )

    def register(self):
        self.growl.register()

    def start(self, title, description):
        self.notify(title, description)

    def success(self, title, description):
        self.notify(title, description)

    def fail(self, title, description):
        self.notify(title=title, description=description)
        
    def notify(self, title, description, icon=None, sticky=False):
        self.growl.notify(noteType=GROWL_NOTIFICATIONS_DEFAULT,
            title=title,
            description=description,
            icon=icon,
            sticky=sticky)

help_text = 'Growl notifications on test run start and stop'

class UnittestGrowl(Plugin):
    """
    Enable Growl notifications
    """
    configSection = 'growl'
    commandLineSwitch = ('G', 'growl', help_text)
    
    def register(self):
        if GrowlNotifier is None:
            raise growlImportError
        Plugin.register(self)
        
    def startTestRun(self, event):
        growl = SimpleNotifier()
        growl.register()
        self.start_time = datetime.datetime.now()
        growl.start("Starting tests...", 'Started at : [%s]' % self.start_time.isoformat())

    def stopTestRun(self, event):
        growl = SimpleNotifier()
        result = event.result
        
        fail_msg = '\n'.join(["Failed: %s" % name for name, ex in result.failures])
        err_msg = '\n'.join(["Error: %s" % name for name, ex in result.errors])

        big_msg = '\n'.join([fail_msg, err_msg])

        self.finish_time = datetime.datetime.now()
            
        delta = self.finish_time - self.start_time
        endtime_msg = 'Completed in  %s.%s seconds' % (delta.seconds, delta.microseconds)
        if result.wasSuccessful():
            growl.success("%s tests run ok" % result.testsRun, endtime_msg)
        else:
            growl.fail("%s tests. %s failed. %s errors." % (result.testsRun, len(result.failures), len(result.errors)), "%s\n%s" % (big_msg, endtime_msg))

