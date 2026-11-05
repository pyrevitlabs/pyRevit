#! python3
"""Run the same hook assertions through the CPython engine."""

import os

probe_path = os.path.join(os.path.dirname(__file__), "handle_event_probe.py")
with open(probe_path) as probe_file:
    exec(compile(probe_file.read(), probe_path, "exec"))
