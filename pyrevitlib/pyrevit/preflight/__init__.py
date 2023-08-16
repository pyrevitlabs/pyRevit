"""Preflight checks framework.

This framework is designed to automate verification and quality control
checks that need to be completed before model is published. The framework works
very similarly to ``unitchecks`` module.

All preflight checks are subclassed from a base class and are recognized
automatically by the preflight module. Each test case, can perform ``setUp()``,
``startTest()``, ``tearDown()``, and ``doCleanups()``.
"""
import os.path as op
import imp
import inspect

from pyrevit.extensions import extensionmgr
from pyrevit.extensions import extpackages as extpkg
from pyrevit.preflight.case import PreflightTestCase


def _grab_test_types(module):
    testtypes = []
    for mem in inspect.getmembers(module):
        mobj = mem[1]
        if inspect.isclass(mobj) \
                and issubclass(mobj, PreflightTestCase) \
                and mobj is not PreflightTestCase:
            testtypes.append(mobj)
    return testtypes


def _get_check_name(check_script):
    script_name = op.splitext(op.basename(check_script))[0]
    return script_name.replace("_check", "")


class PreflightCheck(object):
    """Preflight Check."""

    def __init__(self, extension, check_type, script_path):
        self.check_case = check_type
        self.name = getattr(self.check_case, "name", None) \
            or _get_check_name(script_path)
        self.script_path = script_path

        self.extension = extension.name
        self.author = getattr(self.check_case, "author", None)
        if not self.author:
            self.author = "Unknown"
            extension_pkg = extpkg.get_ext_package_by_name(extension.name)
            if extension_pkg:
                self.author = extension_pkg.author

        desc_lines = getattr(self.check_case, "__doc__", "").strip().split('\n')
        if desc_lines:
            self.subtitle = desc_lines[0]
            self.description = '\n'.join([x.strip() for x in desc_lines[1:]])


def run_preflight_check(check, doc, output):
    """Run a preflight check.

    Args:
        check (PreflightCheck): preflight test case object
        doc (Document): Revit document
        output (pyrevit.output.PyRevitOutputWindow): output window wrapper
    """
    check_case = check.check_case()
    check_case.setUp(doc=doc, output=output)
    check_case.startTest(doc=doc, output=output)
    check_case.tearDown(doc=doc, output=output)
    check_case.doCleanups(doc=doc, output=output)


def get_all_preflight_checks():
    """Find all the preflight checks in installed extensions."""
    preflight_checks = []
    # get all installed ui extensions
    for ext in extensionmgr.get_installed_ui_extensions():
        # find the checks in the extension
        for check_script in ext.get_checks():
            # load the check source file so all the checks can be extracted
            check_mod = \
                imp.load_source(_get_check_name(check_script), check_script)
            # extract the checks and wrap
            for check_type in _grab_test_types(check_mod):
                preflight_checks.append(
                    PreflightCheck(ext, check_type, check_script)
                )
    return preflight_checks
