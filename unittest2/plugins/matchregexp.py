import unittest2
from unittest2.events import events, addOption

import re

def matchRegexp(event):
    pattern = event.pattern
    name = event.name
    event.handled = True
    # path = event.path
    return re.match(pattern, name)

def enable():
    events.matchPath += matchRegexp
    unittest2.loader.DEFAULT_PATTERN = r'test[_a-z]\w*\.py$'

help_text = ('Match filenames during test discovery'
             ' with regular expressions instead of glob')
addOption(enable, 'R', 'match-regexp', help_text)