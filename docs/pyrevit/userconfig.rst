==================
pyrevit.userconfig
==================

Usage
*****

This module handles the reading and writing of the pyRevit configuration files.
It's been used extensively by pyRevit sub-modules. :obj:`user_config` is
set up automatically in the global scope by this module and can be imported
into scripts and other modules to access the default configurations.

Example:

    >>> from pyrevit.userconfig import user_config
    >>> user_config.add_section('newsection')
    >>> user_config.newsection.property = value
    >>> user_config.newsection.get('property', default_value)
    >>> user_config.save_changes()


The :obj:`user_config` object is also the destination for reading and writing
configuration by pyRevit scripts through :func:`get_config` of
:mod:`pyrevit.scripts` module. Here is the function source:

.. literalinclude:: ../../pyrevitlib/pyrevit/script.py
    :pyobject: get_config

Example:

    >>> from pyrevit import script
    >>> cfg = script.get_config()
    >>> cfg.property = value
    >>> cfg.get('property', default_value)
    >>> script.save_changes()


Documentation
*************

.. automodule:: pyrevit.userconfig
    :members:


Implementation
**************

.. literalinclude:: ../../pyrevitlib/pyrevit/userconfig.py
