"""Run the extension credential unit tests from pyrevit.unittests."""

import pkgutil
import traceback

import pyrevit.unittests as tests_pkg
from pyrevit.unittests.runner import run_module_tests

TEST_MODULE = "test_credentials"


def _format_exception_info(exc_info):
    if isinstance(exc_info, tuple) and len(exc_info) == 3:
        try:
            return "".join(
                traceback.format_exception(exc_info[0], exc_info[1], exc_info[2])
            )
        except Exception:
            return str(exc_info)
    return str(exc_info)


def _print_result_details(module_name, result):
    skipped = len(getattr(result, "skipped", []))
    if skipped:
        print("\n{} test(s) skipped in {}".format(skipped, module_name))

    for label, issues in (("ERROR", result.errors), ("FAILURE", result.failures)):
        if not issues:
            continue

        print("\n{} details for {}:".format(label, module_name))
        for test_obj, exc_info in issues:
            print(" - {} {}".format(label, test_obj))
            print(_format_exception_info(exc_info))


def _assert_store_is_usable():
    """Report the store's own state before the tests run.

    The crypto tests skip when DPAPI is unavailable, which is correct but
    indistinguishable from "all green" in a summary line. Printing what the
    store reports keeps a skip visible, which matters because a silently
    unusable store means tokens are never persisted at all.
    """
    from pyrevit.coreutils import credentials

    print("Credential store available: {}".format(credentials.is_available()))
    if not credentials.is_available():
        print(
            "WARNING: this runtime cannot seal credentials. The crypto tests "
            "will skip, and any token entered in the extension manager will not "
            "be persisted."
        )


credentials_test_module = "{}.{}".format(tests_pkg.__name__, TEST_MODULE)

print("Running {}".format(credentials_test_module))
_assert_store_is_usable()

module = __import__(credentials_test_module, fromlist=["*"])
result = run_module_tests(module)
_print_result_details(credentials_test_module, result)

print("\n" + "=" * 40)
if not result.wasSuccessful():
    raise AssertionError("Credential unit test failures in {}".format(TEST_MODULE))

print("All credential unit tests passed.")
