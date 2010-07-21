import unittest2
from unittest2.events import events, addOption, getConfig

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
    events.matchPath += matchRegexp
    unittest2.loader.DEFAULT_PATTERN = r'test.*\.py$'

options = getConfig()

alwaysOn = False
matchFullPath = False
ourOptions = options.get('matchregexp', {})
if 'always-on' in ourOptions:
    alwaysOn = ourOptions.as_bool('always-on')

if 'full-path' in ourOptions:
    matchFullPath = ourOptions.as_bool('full-path')

if alwaysOn:
    enable()
else:
    help_text = ('Match filenames during test discovery'
                 ' with regular expressions instead of glob')
    addOption(enable, 'R', 'match-regexp', help_text)
