"""Run the extension credential unit tests from pyrevit.unittests."""

import pyrevit.unittests as tests_pkg
from pyrevit.unittests.runner import assert_module_tests_successful

TEST_MODULE = "test_credentials"


def _report_store_state():
    """Report whether this runtime can seal credentials at all.

    The crypto tests skip when the store is unavailable, which is correct but
    indistinguishable from "all green" in a summary line. Printing the store's
    own state keeps a skip visible, because a silently unusable store means
    tokens are never persisted at all - a failure with no other symptom.
    """
    from pyrevit.coreutils import credentials

    print("Credential store available: {}".format(credentials.is_available()))
    if not credentials.is_available():
        print(
            "WARNING: this runtime cannot seal credentials. The crypto tests will "
            "skip, and any token entered in the extension manager will not be "
            "persisted."
        )


credentials_test_module = "{}.{}".format(tests_pkg.__name__, TEST_MODULE)

print("Running {}".format(credentials_test_module))
_report_store_state()

# assert_module_tests_successful, not run_module_tests: the latter only reports,
# and IronPython 2.7's TestResult.wasSuccessful ignores unexpected successes, so
# a red suite would look like a green button.
module = __import__(credentials_test_module, fromlist=["*"])
results = assert_module_tests_successful(module)

print("\n" + "=" * 40)
skipped = len(getattr(results, "skipped", []))
if skipped:
    print("{} test(s) skipped - see the store state above.".format(skipped))
print("All credential unit tests passed.")
