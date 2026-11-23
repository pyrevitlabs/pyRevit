"""Check how the Preflight CAD audit maps the scope choice and a cancel."""

import ast
from pathlib import Path
import types
import unittest
import xml.etree.ElementTree as ET


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

CHECKS = (
    Path(__file__).resolve().parents[4] / "extensions/pyRevitTools.extension/checks"
)
SCRIPT = CHECKS / "cad_audit_check.py"
EN_US = CHECKS / "locale/Checks.ResourceDictionary.en_us.xaml"
XAML_KEY = "{http://schemas.microsoft.com/winfx/2006/xaml}Key"


def _en_us_strings():
    return {node.get(XAML_KEY): node.text for node in ET.parse(str(EN_US)).getroot()}


class _Exited(Exception):
    pass


def _get_user_input(choice):
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    node = next(
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "get_user_input"
    )
    strings = _en_us_strings()
    shown = []

    def show(options, **kwargs):
        shown.append(options)
        return choice

    def exit_script():
        raise _Exited()

    namespace = {
        "_t": strings.__getitem__,
        "forms": types.SimpleNamespace(
            CommandSwitchWindow=types.SimpleNamespace(show=show)
        ),
        "script": types.SimpleNamespace(exit=exit_script),
    }
    exec(compile(ast.Module([node], []), str(SCRIPT), "exec"), namespace)
    return namespace["get_user_input"], shown


class CadAuditScopeTests(unittest.TestCase):
    """The scope dialog returns a label; the audit needs "active view only"."""

    def test_offers_both_scopes(self):
        strings = _en_us_strings()
        get_user_input, shown = _get_user_input(strings["CADAuditInProject"])

        get_user_input()

        self.assertEqual(
            [[strings["CADAuditInProject"], strings["CADAuditInActiveView"]]], shown
        )

    def test_project_choice_audits_the_whole_model(self):
        get_user_input, _ = _get_user_input(_en_us_strings()["CADAuditInProject"])

        self.assertIs(False, get_user_input())

    def test_active_view_choice_audits_the_active_view_only(self):
        get_user_input, _ = _get_user_input(_en_us_strings()["CADAuditInActiveView"])

        self.assertIs(True, get_user_input())

    def test_cancel_exits_the_script(self):
        get_user_input, _ = _get_user_input(None)

        with self.assertRaises(_Exited):
            get_user_input()


if __name__ == "__main__":
    unittest.main()
