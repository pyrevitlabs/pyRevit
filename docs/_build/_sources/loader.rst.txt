==================================
The Loader Module (pyrevit.loader)
==================================

The loader module manages the workflow of loading a new pyRevit session. It's main purpose is to orchestrate the process of finding pyRevit extensions, creating dll assemblies for them, and creating a user interface in the host application.

Everything starts from ``sessionmgr.load_session()`` function...

.. automodule:: pyrevit
    :members:
    :private-members:
    :show-inheritance:
