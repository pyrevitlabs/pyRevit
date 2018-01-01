:mod:`pyrevit.script`
=====================

Usage
*****

See :ref:`scriptmodule`

.. code-block:: python

    from pyrevit import script

    script.clipboard_copy('some text')
    data = script.journal_read('data-key')
    script.exit()


Documentation
*************

.. automodule:: pyrevit.script
    :members:


Implementation
**************

.. literalinclude:: ../../pyrevitlib/pyrevit/script.py
