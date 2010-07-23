"""
Example unittest plugin.

Requires py-Growl.

Code liberally "borrowed" from NoseGrowl:
    http://bitbucket.org/crankycoder/nosegrowl/
"""
from unittest2.events import hooks, addOption, getConfig

import warnings
# py-Growl uses md5
warnings.filterwarnings("ignore", category=DeprecationWarning)

import os
import sys
import re
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

class UnittestGrowl(object):
    """
    Enable Growl notifications
    """

    def start(self, event):
        growl = SimpleNotifier()
        growl.register()
        self.start_time = datetime.datetime.now()
        growl.start("Starting tests...", 'Started at : [%s]' % self.start_time.isoformat())

    def stop(self, event):
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

def enable():
    if GrowlNotifier is None:
        raise growlImportError
    _plugin = UnittestGrowl()
    hooks.testRunStart += _plugin.start
    hooks.testRunStop += _plugin.stop

ourOptions = getConfig('coverage')
alwaysOn = ourOptions.as_bool('always-on', default=False)

def initialise():
    if alwaysOn:
        enable()
    else:
        help_text = 'Growl notifications on test run start and stop'
        addOption(enable, 'G', 'growl', help_text)