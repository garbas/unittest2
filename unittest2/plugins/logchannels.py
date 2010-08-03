from unittest2 import Plugin, addOption

try:
    any
except NameError:
    def any(seq):
        for entry in seq:
            if entry:
                return True
        return False

help_text = 'enable a log channel for output'
class LogChannels(Plugin):

    def __init__(self):
        self.channels = []
        addOption(self.channels, None, 'channel', help_text)
        self.register()
    
    def pluginsLoaded(self, event):
        if not self.channels:
            self.unregister()
        self.channels = set(self.channels)

    def message(self, event):
        # this will *always* be a tuple
        verbosity = event.verbosity

        found = any(verb in self.channels for verb in verbosity)
        if found:
            event.handled = True
            return True
