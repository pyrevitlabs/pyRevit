"""Preflight checks framework.

This framework is designed to automate verification and quality control
checks that need to be completed before model is published. The framework works
very similarly to ``unitchecks`` module.

All preflight checks are subclassed from a base class and are recognized
automatically by the preflight module. Each test case, can perform ``setUp()``,
``startTest()``, ``tearDown()``, and ``doCleanups()``.
"""

import os.path as op
import inspect
import sys

try:
    import imp
except ImportError:
    imp = None

from pyrevit.coreutils.logger import get_logger
from pyrevit.extensions import COMP_CHECK_POSTFIX
from pyrevit.extensions import extensionmgr
from pyrevit.extensions import extpackages as extpkg
from pyrevit.preflight.case import PreflightTestCase

mlogger = get_logger(__name__)


def _load_check_with_imp(name, script_path):
    return imp.load_source(name, script_path)


def _load_check_with_importlib(name, script_path):
    from importlib import util

    module_name = "pyrevit_preflight_check_" + name
    spec = util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load check script: %s" % script_path)
    module = util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module


_load_check_module = (
    _load_check_with_imp if imp is not None else _load_check_with_importlib
)


def _grab_test_types(module):
    testtypes = []
    for mem in inspect.getmembers(module):
        mobj = mem[1]
        if (
            inspect.isclass(mobj)
            and issubclass(mobj, PreflightTestCase)
            and mobj is not PreflightTestCase
        ):
            testtypes.append(mobj)
    return testtypes


def _get_check_name(check_script):
    file_name = op.basename(check_script)
    if file_name.lower().endswith(COMP_CHECK_POSTFIX):
        return file_name[: -len(COMP_CHECK_POSTFIX)]
    return op.splitext(file_name)[0]


class PreflightCheck(object):
    """Preflight Check."""

    def __init__(self, extension, check_type, script_path):
        self.check_case = check_type
        self.name = getattr(self.check_case, "name", None) or _get_check_name(
            script_path
        )
        self.script_path = script_path

        self.extension = extension.name
        self.author = getattr(self.check_case, "author", None)
        if not self.author:
            self.author = "Unknown"
            extension_pkg = extpkg.get_ext_package_by_name(extension.name)
            if extension_pkg:
                self.author = extension_pkg.author

        doc_str = (getattr(self.check_case, "__doc__", None) or "").strip()
        if not doc_str:
            mlogger.error(
                "PreflightCheck '%s' in '%s' has no docstring -- "
                "add a class-level docstring (first line becomes the subtitle).",
                self.name,
                op.basename(script_path),
            )
        desc_lines = doc_str.split("\n") if doc_str else [""]
        self.subtitle = desc_lines[0]
        self.description = "\n".join(x.strip() for x in desc_lines[1:])


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
            try:
                check_mod = _load_check_module(
                    _get_check_name(check_script), check_script
                )
            except Exception as load_ex:
                mlogger.error(
                    "Skipping preflight check script %s: %s", check_script, load_ex
                )
                continue
            # extract the checks and wrap
            for check_type in _grab_test_types(check_mod):
                preflight_checks.append(PreflightCheck(ext, check_type, check_script))
    return preflight_checks
