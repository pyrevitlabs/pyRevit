"""Prime a non-persistent IronPython engine for the Rocket Mode scope test."""

from pyrevit import script


output = script.get_output()
output.set_title("Rocket Mode Cache Warmup")
output.print_md("# Rocket Mode Cache Warmup")
output.print_md("Run Rocket Mode Scope Test next without reloading pyRevit.")
