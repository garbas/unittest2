import unittest2
from unittest2.config import getConfig
from unittest2.events import hooks, addDiscoveryOption

import re

REGEXP_PATTERN = r'test.*\.py$'

def matchRegexp(event):
    event.handled = True
    if matchFullPath:
        return re.match(event.pattern, event.path)
    return re.match(event.pattern, event.name)


def enable():
    hooks.matchPath += matchRegexp
    if not pattern:
        pattern = REGEXP_PATTERN
    unittest2.loader.DEFAULT_PATTERN = pattern

ourOptions = getConfig('matchregexp')
alwaysOn = ourOptions.as_bool('always-on', default=False)
matchFullPath = ourOptions.as_bool('full-path', default=False)
pattern = ourOptions.as_str('pattern', default=None)

if alwaysOn:
    enable()
else:
    help_text = ('Match filenames during test discovery'
                 ' with regular expressions instead of glob')
    addDiscoveryOption(enable, 'R', 'match-regexp', help_text)
