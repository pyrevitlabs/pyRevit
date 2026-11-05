"""Run the agent runtime end-to-end tests from IronPython."""

# pylint: skip-file
import agent_harness
import agent_modify_tests
import agent_pipe_tests
import agent_query_tests
import agent_requests_tests
import agent_settings_tests
import agent_validation_tests

agent_harness.run_suites(
    [
        agent_requests_tests,
        agent_validation_tests,
        agent_query_tests,
        agent_modify_tests,
        agent_settings_tests,
        agent_pipe_tests,
    ]
)
