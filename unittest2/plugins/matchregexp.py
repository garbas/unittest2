import unittest2
from unittest2.config import getConfig
from unittest2.events import hooks, addDiscoveryOption

import re


def matchRegexp(event):
    event.handled = True
    if matchFullPath:
        return re.match(event.pattern, event.path)
    return re.match(event.pattern, event.name)


def enable():
    hooks.matchPath += matchRegexp
    unittest2.loader.DEFAULT_PATTERN = r'test.*\.py$'

ourOptions = getConfig('matchregexp')
alwaysOn = ourOptions.as_bool('always-on', default=False)
matchFullPath = ourOptions.as_bool('full-path', default=False)

if alwaysOn:
    enable()
else:
    help_text = ('Match filenames during test discovery'
                 ' with regular expressions instead of glob')
    addDiscoveryOption(enable, 'R', 'match-regexp', help_text)
