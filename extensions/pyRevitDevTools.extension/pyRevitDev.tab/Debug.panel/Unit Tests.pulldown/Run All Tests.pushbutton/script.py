"""Run all hosted unit tests from pyrevit.unittests."""

import pkgutil
import traceback
import unittest

import pyrevit.unittests as tests_pkg
from pyrevit.unittests.runner import run_module_tests

TEST_MODULE_PREFIX = "test_"


def _discover_test_modules():
    module_names = []
    for _, module_name, is_package in pkgutil.iter_modules(tests_pkg.__path__):
        if not is_package and module_name.startswith(TEST_MODULE_PREFIX):
            module_names.append(module_name)
    return sorted(module_names)


def _format_exception_info(exc_info):
    try:
        return "".join(
            traceback.format_exception(exc_info[0], exc_info[1], exc_info[2])
        )
    except Exception:
        return str(exc_info)


def _print_result_details(module_name, result):
    skipped = len(getattr(result, "skipped", []))
    if skipped:
        print("{}: {} test(s) skipped".format(module_name, skipped))

    for label, issues in (("ERROR", result.errors), ("FAILURE", result.failures)):
        if not issues:
            continue

        print("\n{} details for {}:".format(label, module_name))
        for test_obj, exc_info in issues:
            print(" - {} {}".format(label, test_obj))
            print(_format_exception_info(exc_info))


test_modules = _discover_test_modules()
if not test_modules:
    raise RuntimeError(
        "No unit test modules found with prefix '{}' in {}".format(
            TEST_MODULE_PREFIX,
            tests_pkg.__name__,
        )
    )

print("Running all pyRevit unit tests:")
for module_name in test_modules:
    print(" - {}".format(module_name))

failures = []
for module_name in test_modules:
    qualified_name = "{}.{}".format(tests_pkg.__name__, module_name)
    print("\nRunning {}".format(qualified_name))
    try:
        module = __import__(qualified_name, fromlist=["*"])
        result = run_module_tests(module)
        if not result.wasSuccessful():
            _print_result_details(qualified_name, result)
            failures.append((qualified_name, result))
        else:
            _print_result_details(qualified_name, result)
    except unittest.SkipTest as skip_err:
        print("{}: SKIPPED ({})".format(qualified_name, skip_err))
    except Exception as exec_err:
        print("\nERROR running {}: {}".format(qualified_name, exec_err))
        failures.append((qualified_name, None))

print("\n" + "=" * 40)
if failures:
    failed_names = [name for name, _ in failures]
    raise AssertionError("Unit test failures: {}".format(", ".join(failed_names)))

print("All {} unit test modules passed.".format(len(test_modules)))
