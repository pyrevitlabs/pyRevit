"""Support for scripts executed by the pyRevit agent host.

The agent host (``PyRevitLabs.PyRevit.Runtime.Agent`` in the runtime) receives
Python source from a coding agent over a local named pipe and runs it through
the regular pyRevit script engines. ``pyrevit.agent._runner`` is the
in-engine half of that contract.

Agent scripts get ``doc``, ``uidoc``, ``app``, ``uiapp``, ``DB``, ``UI``,
``inputs`` and ``kit`` (:mod:`pyrevit.agent.kit`) injected, and return data by
assigning ``result``.
See ``docs/agent-runtime.md`` for the design.
"""
