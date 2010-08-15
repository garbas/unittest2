import os
import sys
from unittest2 import getConfig, loadPlugin

defaultPath = '~/.unittest'

config = getConfig('plugins-dir')
thePath = config.get('path', defaultPath)
excludedPlugins = getConfig('unittest')['excluded-plugins']

on = config.as_bool('always-on', default=False)

def loadPlugins(thePath):
    if not os.path.isdir(thePath):
        return
    sys.path.append(thePath)
    for entry in os.listdir(thePath):
        fullPath = os.path.join(thePath, entry)
        if entry.lower().endswith('.py') and os.path.isfile(fullPath):
            name = entry[:-3]
            if name in excludedPlugins:
                continue
            loadPlugin(name)
        elif (os.path.isdir(fullPath) and 
              os.path.isfile(os.path.join(fullPath, '__init__.py'))):
            if entry not in excludedPlugins:
                loadPlugin(entry)

if on:
    loadPlugins(os.path.expanduser(thePath))