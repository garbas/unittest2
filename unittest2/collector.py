from unittest2.loader import defaultTestLoader

def collector():
    return defaultTestLoader.discover('.')
