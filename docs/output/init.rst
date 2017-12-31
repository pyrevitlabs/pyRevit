:mod:`pyrevit.output`
=====================

Usage
*************

This module provides access to the output window for the currently running
pyRevit command. The proper way to access this wrapper object is through
the :func:`get_output` of :mod:`pyrevit.script` module. This method, in return
uses the `pyrevit.output` module to get access to the output wrapper.

Example:
    >>> from pyrevit import script
    >>> output = script.get_output()

Here is the source of :func:`pyrevit.script.get_output`. As you can see this
functions calls the :func:`pyrevit.output.get_output` to receive the output wrapper.

.. literalinclude:: ../../pyrevitlib/pyrevit/script.py
    :pyobject: get_output


Documentation
*************

.. automodule:: pyrevit.output
    :members:

Implementation
**************

.. literalinclude:: ../../pyrevitlib/pyrevit/output/__init__.py
