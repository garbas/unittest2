import unittest2
from unittest2.events import hooks, addOption, getConfig

import re


def matchRegexp(event):
    pattern = event.pattern
    name = event.name
    event.handled = True
    path = event.path
    if matchFullPath:
        return re.match(pattern, path)
    return re.match(pattern, name)


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
    addOption(enable, 'R', 'match-regexp', help_text)
