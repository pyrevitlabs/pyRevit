"""Check the agent library integration from inside Revit."""

# pylint: skip-file
import agent_harness
import agent_library_tests

agent_harness.run_suites([agent_library_tests])
