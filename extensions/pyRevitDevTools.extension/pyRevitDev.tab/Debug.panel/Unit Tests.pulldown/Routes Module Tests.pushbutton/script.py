"""Run all routes unit tests from pyrevit.unittests."""

import pkgutil
import traceback

import pyrevit.unittests as tests_pkg
from pyrevit.unittests.runner import run_module_tests


__context__ = 'zero-doc'


TEST_MODULE_PREFIX = 'test_routes_'


def _discover_routes_modules():
    module_names = []
    for _, module_name, is_package in pkgutil.iter_modules(tests_pkg.__path__):
        if not is_package and module_name.startswith(TEST_MODULE_PREFIX):
            module_names.append(module_name)
    return sorted(module_names)


def _import_module(qualified_name):
    return __import__(qualified_name, fromlist=['*'])


def _format_exception_info(exc_info):
    if isinstance(exc_info, tuple) and len(exc_info) == 3:
        try:
            return ''.join(
                traceback.format_exception(exc_info[0], exc_info[1], exc_info[2])
            )
        except Exception:
            return str(exc_info)
    return str(exc_info)


def _print_result_details(module_name, result):
    for label, issues in (("ERROR", result.errors), ("FAILURE", result.failures)):
        if not issues:
            continue

        print("\n{} details for {}:".format(label, module_name))
        for test_obj, exc_info in issues:
            print(" - {} {}".format(label, test_obj))
            print(_format_exception_info(exc_info))


routes_test_modules = _discover_routes_modules()
if not routes_test_modules:
    raise RuntimeError(
        "No routes unit test modules found with prefix '{}' in {}".format(
            TEST_MODULE_PREFIX,
            tests_pkg.__name__,
        )
    )

print('Discovered routes unit test modules:')
for module_name in routes_test_modules:
    print(' - {}'.format(module_name))

failures = []
for module_name in routes_test_modules:
    qualified_name = '{}.{}'.format(tests_pkg.__name__, module_name)
    print('\nRunning {}'.format(qualified_name))
    module = _import_module(qualified_name)
    result = run_module_tests(module)
    if not result.wasSuccessful():
        _print_result_details(qualified_name, result)
        failures.append(qualified_name)

if failures:
    raise AssertionError(
        'Routes unit test failures: {}'.format(', '.join(failures))
    )

print('\nAll routes unit tests passed.')
