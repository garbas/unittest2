unittest2 is a backport of the new features added to the unittest testing
framework in Python 2.7. It is tested to run on Python 2.4 - 2.6.

To use unittest2 instead of unittest simply replace ``import unittest`` with
``import unittest2``.

unittest2 is maintained in a mercurial repository. The issue tracker is on
google code:

* `unittest2 hg <http://hg.python.org/unittest2>`_
* `unittest2 issue tracker <http://code.google.com/p/unittest-ext/issues/list>`_
* `Article / Docs: New features in unittest <http://www.voidspace.org.uk/python/articles/unittest2.shtml>`_.


Classes in unittest2 derive from the appropriate classes in unittest, so it
should be possible to use the unittest2 test running infrastructure without
having to switch all your tests to using unittest2 immediately. Similarly
you can use the new assert methods on ``unittest2.TestCase`` with the standard
unittest test running infrastructure. Not all of the new features in unittest2
will work with the standard unittest test loaders and runners however.

New features include:

* ``addCleanups`` - better resource management
* *many* new assert methods including better defaults for comparing lists,
  sets, dicts unicode strings etc and the ability to specify new default methods
  for comparing specific types
* ``assertRaises`` as context manager, with access to the exception afterwards 
* test discovery and new command line options (including failfast and better
  handling of ctrl-C during test runs)
* class and module level fixtures: ``setUpClass``, ``tearDownClass``,
  ``setUpModule``, ``tearDownModule``
* test skipping and expected failures
* new ``delta`` keyword argument to ``assertAlmostEquals`` for more useful
  comparison and for comparing non-numeric objects (like datetimes)
* ``load_tests`` protocol for loading tests from modules or packages 
* ``startTestRun`` and ``stopTestRun`` methods on TestResult
* various other API improvements and fixes

.. note:: Command line usage

    In Python 2.7 you invoke the unittest command line features (including test
    discover) with ``python -m unittest <args>``. As unittest is a package, and
    the ability to invoke packages with ``python -m ...`` is new in Python 2.7,
    we can't do this for unittest2.
    
    Instead unittest2 comes with a script ``unit2``. 
    `Command line usage <http://docs.python.org/dev/library/unittest.html#command-line-interface>`_::
    
        unit2 discover
        unit2 -v test_module
    
    There is also a copy of this script called ``unit2.py``, useful for Windows
    which uses file-extensions rather than shebang lines to determine what
    program to execute files with. Both of these scripts are installed by
    distutils.

Until I write proper documentation, the best information on all the new features
is the development version of the Python documentation for Python 2.7:

* http://docs.python.org/dev/library/unittest.html

Look for notes about features added or changed in Python 2.7.

.. note::

    unittest2 is already in use for development for development of 
    `distutils2 <http://hg.python.org/distutils2>`_.

Differences
===========

Differences between unittest2 and unittest in Python 2.7:

``assertItemsEqual`` does not silence Py3k warnings as this uses
``warnings.catch_warnings()`` which is new in Python 2.6 (and is used as a
context manager which would be a pain to make work with Python 2.4).

The underlying dictionary storing the type equality functions on TestCase is a
custom object rather than a real dictionary. This allows TestCase instances to
be deep-copyable on Python versions prior to 2.7.

``TestCase.longMessage`` defaults to True because it is better. It defaults to
False in Python 2.7 for backwards compatibility reasons.

``python -m package`` doesn't work until Python 2.7. The command line features
of unittest2 are provided by a ``unit2`` (and ``unit2.py``) script instead.


CHANGELOG
=========

2010/04/08 - 0.4.0
------------------

Addition of ``removeHandler`` for removing the control-C handler.

``delta`` keyword argument for ``assertAlmostEqual`` and
``assertNotAlmostEqual``.

Addition of -b command line option (and ``TestResult.buffer``) for buffering 
stdout / stderr during test runs.

Addition of ``TestCase.assertNotRegexpMatches``.

Allow test discovery using dotted module names instead of a path.

All imports requiring the signal module are now optional, for compatiblity
with IronPython (or other platforms without this module).

Tests fixed to be compatible with nosetest.


2010/03/26 - 0.3.0
------------------

``assertSameElements`` removed and ``assertItemsEqual`` added; assert that
sequences contain the same elements.

Addition of -f/--failfast command line option, stopping test run on first
failure or error.

Addition of -c/--catch command line option for better control-C handling during
test runs.

Added ``BaseTestSuite``, for use by frameworks that don't want to support shared
class and module fixtures.

Skipped test methods no longer have ``setUp`` and ``tearDown`` called around
them.

Faulty ``load_tests`` functions no longer halt test discovery.

Using non-strings for failure messages now works.

Potential for ``UnicodeDecodeError`` whilst creating failure messages fixed.

Split out monolithic test module into a package.

BUGFIX: Correct usage message now shown for unit2 scripts.

BUGFIX: ``__unittest`` in module globals trims frames from that module in
reported stacktraces.


2010/03/06 - 0.2.0
------------------

The ``TextTestRunner`` is now compatible with old result objects and standard
(non-TextTestResult) ``TestResult`` objects.

``setUpClass`` / ``tearDownClass`` / ``setUpModule`` / ``tearDownModule`` added.


2010/02/22 - 0.1.6
------------------

Fix for compatibility with old ``TestResult`` objects. New tests can now be run
with nosetests (with a DeprecationWarning for ``TestResult`` objects without
methods to support skipping etc).


0.1
---

Initial release.


TODO
====

For *before* the Python 2.7 release:

* Addition of ``removeHandler`` to 2.7?
* Making ``removeHandler`` a context manager?
* Tests for command line handling of -b
* Tests for dotted path discovery
* Docstrings for assertRegexpMatches and assertNotRegexpMatches
* Issues 8301, 8302 and 8303 on the Python bug tracker
* Document ``BaseTestSuite`` and ``_ErrorHolder``
