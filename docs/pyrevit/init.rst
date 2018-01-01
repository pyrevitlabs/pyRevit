:mod:`pyrevit`
==============

Usage
*****

.. code-block:: python

    from pyrevit import DB, UI
    from pyrevit import PyRevitException, PyRevitIOError

    # pyrevit module has global instance of the
    # _HostAppPostableCommand and _ExecutorParams classes already created
    # import and use them like below
    from pyrevit import HOST_APP
    from pyrevit import EXEC_PARAMS


Documentation
*************

.. autoclass:: pyrevit.PyRevitException

.. autoclass:: pyrevit.PyRevitIOError

.. autoclass:: pyrevit._HostAppPostableCommand

.. autoclass:: pyrevit._HostApplication
    :members:

.. autoclass:: pyrevit._ExecutorParams
    :members:


Implementation
**************

.. literalinclude:: ../../pyrevitlib/pyrevit/__init__.py
