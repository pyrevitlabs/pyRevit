"""Portable tests for XAML preparation and shared input-dialog behavior.

Native WPF loading and modal interaction are covered by the in-host suite.
"""

import ast
import datetime
import enum
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from xml.dom import minidom


FORMS = Path(__file__).resolve().parents[2] / "pyrevitlib" / "pyrevit" / "forms"


def _load_xaml_helpers():
    spec = importlib.util.spec_from_file_location("forms_xaml", FORMS / "_xaml.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_dialog():
    tree = ast.parse((FORMS / "dialogs.py").read_text(encoding="utf-8"))
    tree.body = [
        node for node in tree.body if getattr(node, "name", None) == "GetValueWindow"
    ]
    scope = {
        "TemplateUserInputWindow": object,
        "datetime": datetime,
        "_backend": SimpleNamespace(items_source=lambda values: values),
    }
    exec(compile(tree, "dialogs.py", "exec"), scope)
    return scope["GetValueWindow"]


def _load_usage_inventory():
    script = Path(__file__).resolve().with_name("forms_usage.py")
    spec = importlib.util.spec_from_file_location("forms_usage", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.inventory(FORMS.parents[2])


class XamlPreparationTests(unittest.TestCase):
    """Keep namespace-sensitive WPF markup intact while deferring events."""

    def test_shipped_input_names_events_and_namespace_prefixes(self):
        """The real input markup keeps resources and element-to-element bindings."""
        helpers = _load_xaml_helpers()
        source = (FORMS / "GetValueWindow.xaml").read_text(encoding="utf-8")
        markup, names, events = helpers.prepare_xaml(
            source, ["file:///C:/forms/Theme.xaml"]
        )
        document = minidom.parseString(markup)
        self.assertIn("okayButton", names)
        self.assertIn(("okayButton", "Click", "select"), events)
        self.assertIn(("stringValue_tb", "TextChanged", "string_value_changed"), events)
        button = document.getElementsByTagName("Button")[0]
        self.assertFalse(button.hasAttribute("Click"))
        self.assertIn("{x:Type DatePicker}", markup)
        self.assertIn('xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"', markup)
        self.assertIn("file:///C:/forms/Theme.xaml", markup)
        self.assertIn("{Binding ElementName=numberPicker", markup)

    def test_event_without_name_receives_generated_name(self):
        """Unnamed controls remain reachable for deferred event attachment."""
        markup, names, events = _load_xaml_helpers().prepare_xaml(
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation">'
            '<Button Click="select"/></Window>',
            [],
        )
        self.assertEqual(1, len(events))
        self.assertIn(events[0][0], names)
        self.assertEqual(("Click", "select"), events[0][1:])
        self.assertNotIn('Click="select"', markup)

    def test_existing_resource_dictionary_keeps_entries_and_merge_order(self):
        """Authored resources retain precedence over injected resources."""
        markup, _, _ = _load_xaml_helpers().prepare_xaml(
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation">'
            "<Window.Resources><ResourceDictionary><ResourceDictionary.MergedDictionaries>"
            '<ResourceDictionary Source="custom.xaml"/>'
            '</ResourceDictionary.MergedDictionaries><Style TargetType="Button"/>'
            "</ResourceDictionary></Window.Resources></Window>",
            ["theme.xaml", "locale.xaml"],
        )
        document = minidom.parseString(markup)
        sources = [
            node.getAttribute("Source")
            for node in document.getElementsByTagName("ResourceDictionary")
            if node.hasAttribute("Source")
        ]
        self.assertEqual(["theme.xaml", "locale.xaml", "custom.xaml"], sources)
        self.assertEqual(1, len(document.getElementsByTagName("Style")))

    def test_bundled_xaml_handlers_are_deferred(self):
        """Every bundled custom handler uses a CPython-deferred WPF event."""
        audit = _load_usage_inventory()["xaml_events"]
        self.assertEqual([], audit["unparsed"])
        self.assertEqual([], audit["unsupported"])

    def test_inventory_reports_cpython_modal_and_unsupported_boundaries(self):
        """Bundled forms usage stays within the documented CPython boundary."""
        coverage = _load_usage_inventory()["cpython"]
        self.assertEqual(355, coverage["supported_references"])
        self.assertEqual(26, coverage["modal_only_references"])
        self.assertEqual(15, coverage["unsupported_references"])
        self.assertEqual({"WPFWindow"}, set(coverage["modal_only"]))
        self.assertEqual(
            {
                "WPFPanel",
                "activate_open_window",
                "get_dockable_panel",
                "is_registered_dockable_panel",
                "open_dockable_panel",
                "register_dockable_panel",
                "toggle_dockable_panel",
            },
            set(coverage["unsupported"]),
        )

    def test_template_names_remain_in_their_own_namescope(self):
        """Template names are not exposed as window fields."""
        _, names, _ = _load_xaml_helpers().prepare_xaml(
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" '
            'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
            '<Window.Resources><ControlTemplate x:Key="t"><Border x:Name="inner"/>'
            '</ControlTemplate></Window.Resources><Button x:Name="outer"/></Window>',
            [],
        )
        self.assertEqual(["outer"], names)


class FormsExportsTests(unittest.TestCase):
    """Keep accidental legacy exports compatible as well as the intended API."""

    def test_ironpython_public_names_match_the_pre_extraction_surface(self):
        """An explicit export list must not drop previously importable names."""
        fixture = Path(__file__).parent / "fixtures" / "forms_ironpython_exports.json"
        expected = json.loads(fixture.read_text(encoding="utf-8"))
        tree = ast.parse((FORMS / "_ipy.py").read_text(encoding="utf-8"))
        exports = next(
            node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "__all__"
                for target in node.targets
            )
        )
        self.assertEqual(expected, ast.literal_eval(exports))
        defined = set()
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                defined.add(node.name)
            elif isinstance(node, ast.Assign):
                defined.update(
                    target.id for target in node.targets if isinstance(target, ast.Name)
                )
            elif isinstance(node, ast.Import):
                defined.update(
                    item.asname or item.name.split(".")[0] for item in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                defined.update(item.asname or item.name for item in node.names)
        self.assertFalse(set(expected) - defined)


class InputResponseTests(unittest.TestCase):
    """Retain input values before closing and keep cancellation empty."""

    def test_response_is_ready_when_closed_handlers_run(self):
        """Close callbacks see the accepted value rather than an empty response."""
        dialog = _load_dialog()()
        dialog.value_type = "string"
        dialog.stringValue_tb = SimpleNamespace(Text="accepted")
        observed = []
        dialog.Close = lambda: observed.append(dialog.response)
        dialog.select(None, None)
        self.assertEqual(["accepted"], observed)

    def test_date_and_slider_results_keep_existing_python_types(self):
        """Empty dates remain None and accepted dates become Python datetimes."""
        dialog = _load_dialog()()
        dialog.Close = lambda: None
        dialog.value_type = "date"
        dialog.datePicker = SimpleNamespace(
            SelectedDate=SimpleNamespace(Year=2026, Month=10, Day=26)
        )
        dialog.select(None, None)
        self.assertEqual(datetime.datetime(2026, 10, 26), dialog.response)
        dialog.datePicker.SelectedDate = None
        dialog.select(None, None)
        self.assertIsNone(dialog.response)
        dialog.value_type = "slider"
        dialog.numberPicker = SimpleNamespace(Value=25.0)
        dialog.select(None, None)
        self.assertEqual(25.0, dialog.response)

    def test_reserved_value_disables_accept_then_recovers(self):
        """Validation responds to edits without closing the dialog."""
        dialog = _load_dialog()()
        dialog.reserved_values = ["taken", "taken-too"]
        dialog.stringValue_tb = SimpleNamespace(Text="taken")
        dialog.reservedValuesList = SimpleNamespace(ItemsSource=None)
        dialog.reservedValuesListPanel = object()
        dialog.okayButton = SimpleNamespace(IsEnabled=True)
        dialog.show_element = lambda element: None
        dialog.hide_element = lambda element: None
        dialog.string_value_changed(None, None)
        self.assertFalse(dialog.okayButton.IsEnabled)
        dialog.stringValue_tb.Text = "available"
        dialog.string_value_changed(None, None)
        self.assertTrue(dialog.okayButton.IsEnabled)


class _Result(enum.Enum):
    Nothing = 0
    Ok = 1
    Cancel = 2
    Yes = 3
    No = 4
    Retry = 5
    CommandLink1 = 10
    CommandLink2 = 11


class NativeDialogTests(unittest.TestCase):
    """Task-dialog results must retain their public return and exit contracts."""

    @staticmethod
    def _native_functions(names, scope):
        tree = ast.parse((FORMS / "native.py").read_text(encoding="utf-8"))
        tree.body = [node for node in tree.body if getattr(node, "name", None) in names]
        exec(compile(tree, "native.py", "exec"), scope)
        return scope

    def test_folder_picker_unwraps_a_cpython_window_owner(self):
        """Native dialogs receive the managed root rather than its Python controller."""
        native_owner = object()
        observed = []
        dialog = SimpleNamespace(
            ShowDialog=lambda owner: observed.append(owner) or "ok",
            FileName="chosen-folder",
        )
        scope = {
            "CPDialogs": SimpleNamespace(
                CommonOpenFileDialog=lambda: dialog,
                CommonFileDialogResult=SimpleNamespace(Ok="ok", Cancel="cancel"),
            ),
            "_backend": SimpleNamespace(unwrap=lambda owner: native_owner),
        }
        self._native_functions({"pick_folder"}, scope)
        self.assertEqual("chosen-folder", scope["pick_folder"](owner=object()))
        self.assertEqual([native_owner], observed)

    def test_file_save_and_color_dialogs_keep_their_public_values(self):
        """CPython uses the same native dialog properties and return values."""
        open_dialog = SimpleNamespace(
            ShowDialog=lambda: "ok",
            FileName="single.txt",
            FileNames=["one.txt", "two.txt"],
        )
        save_dialog = SimpleNamespace(FileName="")

        def show_save_dialog():
            save_dialog.FileName = "saved.txt"
            return "ok"

        save_dialog.ShowDialog = show_save_dialog
        color = SimpleNamespace(A=255, R=1, G=2, B=3)

        class ColorDialog(object):
            def __init__(self):
                self.default = None
                self.selected = color

            @property
            def Color(self):
                return self.selected

            @Color.setter
            def Color(self, value):
                self.default = value

            def ShowDialog(self):
                return "ok"

        color_dialog = ColorDialog()
        created = []

        def open_file_dialog():
            created.append(open_dialog)
            return open_dialog

        def save_file_dialog():
            created.append(save_dialog)
            return save_dialog

        def color_dialog_factory():
            created.append(color_dialog)
            return color_dialog

        scope = {
            "Forms": SimpleNamespace(
                OpenFileDialog=open_file_dialog,
                SaveFileDialog=save_file_dialog,
                ColorDialog=color_dialog_factory,
                DialogResult=SimpleNamespace(OK="ok"),
            ),
            "System": SimpleNamespace(
                Drawing=SimpleNamespace(
                    Color=SimpleNamespace(FromArgb=lambda *values: values)
                )
            ),
            "coreutils": SimpleNamespace(dletter_to_unc=lambda value: "unc:" + value),
        }
        self._native_functions({"pick_file", "save_file", "ask_for_color"}, scope)
        self.assertEqual(
            ["unc:one.txt", "unc:two.txt"],
            scope["pick_file"](multi_file=True, unc_paths=True, title="Open"),
        )
        self.assertEqual(
            "unc:saved.txt",
            scope["save_file"](default_name="unused.txt", unc_paths=True, title="Save"),
        )
        self.assertEqual("#FF010203", scope["ask_for_color"]("#FF000000"))
        self.assertEqual((255, 0, 0, 0), color_dialog.default)

    def _alert(self, result, **kwargs):
        tree = ast.parse((FORMS / "native.py").read_text(encoding="utf-8"))
        tree.body = [
            node for node in tree.body if getattr(node, "name", None) == "alert"
        ]
        dialog = SimpleNamespace(Show=lambda: result, AddCommandLink=lambda *args: None)
        scope = {
            "EXEC_PARAMS": SimpleNamespace(command_name="Test"),
            "UI": SimpleNamespace(
                TaskDialog=lambda title: dialog,
                TaskDialogResult=_Result,
                TaskDialogCommonButtons=SimpleNamespace(
                    Yes=1, Ok=2, Cancel=4, No=8, Retry=16
                ),
                TaskDialogCommandLinkId=object(),
                TaskDialogIcon=SimpleNamespace(
                    TaskDialogIconWarning=1,
                    TaskDialogIconShield=2,
                    TaskDialogIconInformation=3,
                    TaskDialogIconError=4,
                    TaskDialogIconNone=0,
                ),
            ),
            "coreutils": SimpleNamespace(
                get_enum_none=lambda kind: _Result.Nothing if kind is _Result else 0,
                get_enum_values=lambda kind: (
                    list(_Result) if kind is _Result else [0, 1]
                ),
            ),
            "System": SimpleNamespace(
                Convert=SimpleNamespace(ToInt32=lambda value: value.value)
            ),
            "versionmgr": SimpleNamespace(
                get_pyrevit_version=lambda: SimpleNamespace(
                    get_formatted=lambda: "test"
                )
            ),
            "mlogger": SimpleNamespace(
                debug=lambda *args: None, warning=lambda *args: None
            ),
            "sys": __import__("sys"),
        }
        exec(compile(tree, "native.py", "exec"), scope)
        return scope["alert"]("Message", **kwargs)

    def test_accept_cancel_and_negative_results(self):
        """Native result enums map to the same booleans on both engines."""
        for result in (_Result.Ok, _Result.Yes, _Result.Retry):
            self.assertTrue(self._alert(result))
        for result in (_Result.Cancel, _Result.No, _Result.Nothing):
            self.assertFalse(self._alert(result))

    def test_command_links_do_not_require_sortable_enum_objects(self):
        """Pythonnet enums need an explicit numeric ordering key."""
        self.assertEqual(
            "Second", self._alert(_Result.CommandLink2, options=["First", "Second"])
        )

    def test_exitscript_preserves_legacy_exit_behavior(self):
        """A negative result still exits when requested by the caller."""
        with self.assertRaises(SystemExit):
            self._alert(_Result.Cancel, exitscript=True)

    def test_warning_delegates_to_the_warning_styled_alert(self):
        """The legacy warning helper remains available through both engines."""
        scope = {"alert": lambda message, *args, **kwargs: (message, kwargs)}
        self._native_functions({"warning"}, scope)
        self.assertEqual(("Message", {"warn_icon": True}), scope["warning"]("Message"))
        self.assertEqual(
            ("Message", {"warn_icon": False}),
            scope["warning"]("Message", warn_icon=False),
        )


if __name__ == "__main__":
    unittest.main()
