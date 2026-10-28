"""Portable tests for XAML preparation and shared input-dialog behavior.

Native WPF loading and modal interaction are covered by the in-host suite.
"""

import ast
import datetime
import enum
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock
from xml.dom import minidom


FORMS = Path(__file__).resolve().parents[2] / "pyrevitlib" / "pyrevit" / "forms"


def _load_xaml_helpers():
    spec = importlib.util.spec_from_file_location("forms_xaml", FORMS / "_xaml.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _PyRevitException(Exception):
    pass


class _InputWindow(object):
    created = []

    def __init__(self, *args, **kwargs):
        _InputWindow.created.append(kwargs)


def _load_dialog_class():
    tree = ast.parse((FORMS / "dialogs.py").read_text(encoding="utf-8"))
    tree.body = [
        node
        for node in tree.body
        if getattr(node, "name", None) == "GetValueWindow"
        or (
            isinstance(node, ast.Assign)
            and any(getattr(t, "id", None) == "VALUE_TYPES" for t in node.targets)
        )
    ]
    scope = {
        "TemplateUserInputWindow": _InputWindow,
        "PyRevitException": _PyRevitException,
        "datetime": datetime,
        "_backend": SimpleNamespace(items_source=lambda values: values),
    }
    exec(compile(tree, "dialogs.py", "exec"), scope)
    return scope["GetValueWindow"]


def _load_dialog():
    dialog_class = _load_dialog_class()
    return lambda: dialog_class.__new__(dialog_class)


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
        markup, names, events, _ = helpers.prepare_xaml(
            source, ["file:///C:/forms/Theme.xaml"]
        )
        document = minidom.parseString(markup)
        handlers = [(event.name, event.event, event.handler) for event in events]
        self.assertIn("okayButton", names)
        self.assertIn(("okayButton", "Click", "select"), handlers)
        self.assertIn(
            ("stringValue_tb", "TextChanged", "string_value_changed"), handlers
        )
        button = document.getElementsByTagName("Button")[0]
        self.assertFalse(button.hasAttribute("Click"))
        self.assertIn("{x:Type DatePicker}", markup)
        self.assertIn('xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"', markup)
        self.assertIn("file:///C:/forms/Theme.xaml", markup)
        self.assertIn("{Binding ElementName=numberPicker", markup)

    def test_event_without_name_receives_generated_name(self):
        """Unnamed controls remain reachable for deferred event attachment."""
        markup, names, events, _ = _load_xaml_helpers().prepare_xaml(
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation">'
            '<Button Click="select"/></Window>',
            [],
        )
        self.assertEqual(1, len(events))
        self.assertIn(events[0].name, names)
        self.assertEqual(("Click", "select"), (events[0].event, events[0].handler))
        self.assertNotIn('Click="select"', markup)

    def test_existing_resource_dictionary_keeps_entries_and_merge_order(self):
        """Authored resources retain precedence over injected resources."""
        markup, _, _, _ = _load_xaml_helpers().prepare_xaml(
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
        self.assertEqual([], audit["template_direct"])

    def test_bundled_scripts_adapt_child_data_contexts(self):
        """Child controls receive models through forms.set_data_context."""
        hazards = _load_usage_inventory()["cpython_hazards"]
        self.assertEqual([], hazards["child_data_context"])

    def test_inventory_reports_full_cpython_forms_coverage(self):
        """Bundled forms usage resolves through the published CPython facade."""
        coverage = _load_usage_inventory()["cpython"]
        self.assertEqual(397, coverage["supported_references"])
        self.assertEqual(0, coverage["modal_only_references"])
        self.assertEqual(0, coverage["host_required_references"])
        self.assertEqual(0, coverage["unsupported_references"])
        self.assertEqual(set(), set(coverage["modal_only"]))
        self.assertEqual(set(), set(coverage["host_required"]))
        self.assertEqual(set(), set(coverage["unsupported"]))

    def test_template_names_remain_in_their_own_namescope(self):
        """Template names are not exposed as window fields."""
        _, names, _, _ = _load_xaml_helpers().prepare_xaml(
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" '
            'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
            '<Window.Resources><ControlTemplate x:Key="t"><Border x:Name="inner"/>'
            '</ControlTemplate></Window.Resources><Button x:Name="outer"/></Window>',
            [],
        )
        self.assertEqual(["outer"], names)

    def test_attribute_line_breaks_survive_reparsing(self):
        """Encoded newlines and tabs in attributes are not normalized to spaces."""
        markup, _, _, _ = _load_xaml_helpers().prepare_xaml(
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation">'
            '<TextBlock Text="Line1&#x0a;Line2&#x09;End"/></Window>',
            [],
        )
        self.assertIn('Text="Line1&#10;Line2&#9;End"', markup)
        text_block = minidom.parseString(markup).getElementsByTagName("TextBlock")[0]
        self.assertEqual("Line1\nLine2\tEnd", text_block.getAttribute("Text"))

    def test_prefixed_wpf_root_keeps_merged_resources_in_the_wpf_namespace(self):
        """Generated resource nodes use the prefix the root binds to WPF."""
        wpf = "http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        markup, _, _, _ = _load_xaml_helpers().prepare_xaml(
            '<w:Window xmlns:w="{}"><w:Grid/></w:Window>'.format(wpf),
            ["theme.xaml"],
        )
        document = minidom.parseString(markup)
        dictionaries = document.getElementsByTagNameNS(wpf, "ResourceDictionary")
        self.assertTrue(dictionaries)
        sources = [node.getAttribute("Source") for node in dictionaries]
        self.assertIn("theme.xaml", sources)
        resources = document.getElementsByTagNameNS(wpf, "Window.Resources")
        self.assertEqual(1, len(resources))

    def test_static_palette_keys_resolve_dynamically(self):
        """Host keys added after parsing are looked up when they exist."""
        markup, _, _, _ = _load_xaml_helpers().prepare_xaml(
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation">'
            '<Border Background="{StaticResource pyRevitAccentBrush}" '
            'BorderBrush="{StaticResource authored}"/></Window>',
            [],
            dynamic_keys={"pyRevitAccentBrush"},
        )
        self.assertIn('Background="{DynamicResource pyRevitAccentBrush}"', markup)
        self.assertIn('BorderBrush="{StaticResource authored}"', markup)

    def test_icon_font_characters_are_not_rewritten(self):
        """Private-use characters stay text; only real line breaks are encoded."""
        markup, _, _, _ = _load_xaml_helpers().prepare_xaml(
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation">'
            '<TextBlock Text="&#xE000;&#xE001;&#xE002;"/></Window>',
            [],
        )
        text_block = minidom.parseString(markup).getElementsByTagName("TextBlock")[0]
        self.assertEqual("", text_block.getAttribute("Text"))

    def test_resolved_clr_events_outside_the_allowlist_are_deferred(self):
        """Any attribute the backend reports as an event is detached for binding."""
        markup, names, events, _ = _load_xaml_helpers().prepare_xaml(
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation">'
            '<Button MouseMove="moved" Content="Go"/></Window>',
            [],
            is_event=lambda type_name, attribute: (
                (type_name, attribute) == ("Button", "MouseMove")
            ),
        )
        helpers = _load_xaml_helpers()
        self.assertEqual(
            [helpers.NamedEvent(names[0], "MouseMove", "moved", False)], events
        )
        self.assertNotIn("MouseMove", markup)
        self.assertIn('Content="Go"', markup)

    def test_custom_template_elements_carry_their_namespace(self):
        """Template targets outside WPF are not mistaken for WPF controls."""
        helpers = _load_xaml_helpers()
        _, _, events, _ = helpers.prepare_xaml(
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" '
            'xmlns:local="clr-namespace:Tools"><Window.Resources>'
            '<DataTemplate x:Key="t" '
            'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
            '<local:Button Click="go"/></DataTemplate></Window.Resources></Window>',
            [],
        )
        self.assertEqual(
            [
                helpers.TemplateEvent(
                    "_pyrevit_template_0", "{clr-namespace:Tools}Button", "Click", "go"
                )
            ],
            events,
        )

    def test_template_events_are_tagged_with_their_authored_element(self):
        """Template handlers match only the element that declared them."""
        markup, _, events, _ = _load_xaml_helpers().prepare_xaml(
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" '
            'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
            '<Window.Resources><DataTemplate x:Key="a"><CheckBox Checked="first"/>'
            '</DataTemplate><DataTemplate x:Key="b"><CheckBox x:Uid="mine" '
            'Checked="second" Unchecked="second"/></DataTemplate></Window.Resources>'
            "</Window>",
            [],
        )
        targets = [(event.uid, event.tag) for event in events]
        self.assertEqual(
            [
                ("_pyrevit_template_0", "CheckBox"),
                ("mine", "CheckBox"),
                ("mine", "CheckBox"),
            ],
            targets,
        )
        self.assertIn('Uid="_pyrevit_template_0"', markup)

    def test_resource_names_record_their_owner_and_key(self):
        """Names inside resource entries are resolved through the dictionary."""
        _, names, events, resource_names = _load_xaml_helpers().prepare_xaml(
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" '
            'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
            '<Window.Resources><ContextMenu x:Key="root"><MenuItem Click="copy"/>'
            "</ContextMenu></Window.Resources><ListView><ListView.Resources>"
            '<ResourceDictionary><ContextMenu x:Key="item"><MenuItem x:Name="copyItem"/>'
            "</ContextMenu></ResourceDictionary></ListView.Resources></ListView>"
            "</Window>",
            [],
        )
        owner, key = resource_names["copyItem"]
        self.assertEqual("item", key)
        self.assertIn(owner, names)
        self.assertNotIn(owner, resource_names)
        self.assertEqual((None, "root"), resource_names[events[0].name])

    def test_initial_state_replays_only_where_ironpython_delivers_it(self):
        """Replay follows attribute order like IronPython's LoadComponent."""
        _, _, events, _ = _load_xaml_helpers().prepare_xaml(
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" '
            'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"><StackPanel>'
            '<RadioButton x:Name="before" IsChecked="True" Checked="mode"/>'
            '<RadioButton x:Name="after" Checked="mode" IsChecked="True"/>'
            '<CheckBox x:Name="implicit" Checked="mode"/>'
            '<ComboBox x:Name="indexed" SelectedIndex="0" SelectionChanged="pick"/>'
            '<ComboBox x:Name="listening" SelectionChanged="pick" SelectedItem="a"/>'
            '<ListBox x:Name="valued" SelectedValue="a" SelectionChanged="pick"/>'
            '<Button x:Name="clicked" Click="go" IsEnabled="True"/>'
            "</StackPanel></Window>",
            [],
        )
        self.assertEqual(
            {
                "before": False,
                "after": True,
                "implicit": True,
                "indexed": False,
                "listening": True,
                "valued": False,
                "clicked": False,
            },
            {event.name: event.replay for event in events},
        )

    def test_section_box_navigator_markup_does_not_replay(self):
        """The shipped IsChecked-before-Checked markup keeps IronPython's silence."""
        source = next(
            (FORMS.parents[2] / "extensions").rglob("SectionBoxNavigator.xaml"), None
        )
        if source is None:
            self.skipTest("SectionBoxNavigator markup is not bundled")
        _, _, events, _ = _load_xaml_helpers().prepare_xaml(
            source.read_text(encoding="utf-8-sig"), []
        )
        level_mode = [
            event for event in events if event.handler == "rb_level_mode_changed"
        ]
        self.assertTrue(level_mode)
        document = minidom.parseString(source.read_text(encoding="utf-8-sig"))
        for event in level_mode:
            node = next(
                node
                for node in document.getElementsByTagName("*")
                if node.getAttribute("x:Name") == event.name
                or node.getAttribute("Name") == event.name
            )
            attributes = list(node.attributes.keys())
            checked_first = "IsChecked" in attributes and attributes.index(
                "IsChecked"
            ) < attributes.index("Checked")
            self.assertEqual(not checked_first, event.replay)

    def test_resource_owner_inside_a_resource_entry_is_resolved_through_it(self):
        """A keyed resource owning its own Resources is found via its dictionary."""
        _, names, _, resource_names = _load_xaml_helpers().prepare_xaml(
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" '
            'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
            '<Window.Resources><ContextMenu x:Key="menu"><ContextMenu.Resources>'
            '<SolidColorBrush x:Key="accent" x:Name="accentBrush"/>'
            "</ContextMenu.Resources></ContextMenu></Window.Resources></Window>",
            [],
        )
        owner, key = resource_names["accentBrush"]
        self.assertEqual("accent", key)
        self.assertIn(owner, names)
        self.assertEqual((None, "menu"), resource_names[owner])


class _NotSupported(Exception):
    def __init__(self, feature_name):
        super(_NotSupported, self).__init__()
        self.feature_name = feature_name


def _load_cpython_facade(package_dir):
    (package_dir / "__init__.py").write_text(
        (FORMS / "__init__.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (package_dir / "_legacy_exports.py").write_text(
        (FORMS / "_legacy_exports.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (package_dir / "extra.py").write_text("VALUE = 1\n", encoding="utf-8")
    (package_dir / "broken.py").write_text(
        "import pyrevit_missing_dependency\n", encoding="utf-8"
    )
    pyrevit = ModuleType("pyrevit")
    pyrevit.__path__ = []
    pyrevit.PyRevitCPythonNotSupported = _NotSupported
    compat = ModuleType("pyrevit.compat")
    compat.IRONPY = False
    common = ModuleType("pyrevit.forms._common")
    common.__all__ = ["ProgressBar"]
    common.ProgressBar = object
    spec = importlib.util.spec_from_file_location(
        "pyrevit.forms",
        package_dir / "__init__.py",
        submodule_search_locations=[str(package_dir)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules.update(
        {
            "pyrevit": pyrevit,
            "pyrevit.compat": compat,
            "pyrevit.forms": module,
            "pyrevit.forms._common": common,
        }
    )
    spec.loader.exec_module(module)
    return module


class CPythonFacadeTests(unittest.TestCase):
    """Resolve submodules lazily and report other names as unsupported."""

    def setUp(self):
        """Load the facade from a scratch package with stubbed pyrevit modules."""
        patcher = mock.patch.dict(sys.modules)
        patcher.start()
        self.addCleanup(patcher.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.forms = _load_cpython_facade(Path(directory.name))

    def test_submodules_import_on_first_access(self):
        """A real submodule is imported rather than reported as unsupported."""
        self.assertEqual(1, self.forms.extra.VALUE)

    def test_unknown_names_are_unsupported_attribute_errors(self):
        """Unknown names keep the not-supported contract and work with hasattr."""
        with self.assertRaises(_NotSupported) as raised:
            getattr(self.forms, "does_not_exist")
        self.assertEqual("pyrevit.forms.does_not_exist", raised.exception.feature_name)
        self.assertIsInstance(raised.exception, AttributeError)
        self.assertFalse(hasattr(self.forms, "does_not_exist"))
        self.assertIsNone(getattr(self.forms, "does_not_exist", None))
        with self.assertRaises(AttributeError):
            getattr(self.forms, "_private")

    def test_unported_legacy_names_keep_the_not_supported_message(self):
        """Importing an IronPython-only export reports the unsupported feature."""
        with self.assertRaises(_NotSupported) as raised:
            exec("from pyrevit.forms import CPDialogs", {})
        self.assertEqual("pyrevit.forms.CPDialogs", raised.exception.feature_name)
        self.assertNotIsInstance(raised.exception, AttributeError)
        with self.assertRaises(_NotSupported):
            hasattr(self.forms, "Autodesk")

    def test_shared_names_shadow_the_legacy_list(self):
        """A legacy name CPython also exports resolves normally."""
        self.assertIs(object, self.forms.ProgressBar)

    def test_unknown_names_fail_as_import_errors(self):
        """``from pyrevit.forms import`` an unknown name is an ImportError."""
        with self.assertRaises(ImportError):
            exec("from pyrevit.forms import does_not_exist", {})

    def test_failed_submodule_import_is_an_absent_name(self):
        """A submodule whose import fails is absent, and keeps the cause."""
        self.assertFalse(hasattr(self.forms, "broken"))
        with self.assertRaises(_NotSupported) as raised:
            getattr(self.forms, "broken")
        self.assertIsInstance(raised.exception, AttributeError)
        self.assertEqual("pyrevit.forms.broken", raised.exception.feature_name)
        self.assertIsInstance(raised.exception.__cause__, ImportError)

    def test_submodule_lookups_are_cached(self):
        """Repeated misses do not search the package again."""
        with mock.patch("importlib.util.find_spec", return_value=None) as find_spec:
            for _ in range(3):
                self.assertFalse(hasattr(self.forms, "missing_name"))
        self.assertEqual(1, find_spec.call_count)


class _Expando(object):
    def __init__(self):
        self.values = {}
        self.handlers = []

    def __getitem__(self, name):
        return self.values[name]

    def __setitem__(self, name, value):
        self.values[name] = value
        for handler in list(self.handlers):
            handler(self, SimpleNamespace(PropertyName=name))

    def edit(self, name, value):
        self[name] = value


class _Notifier(object):
    def __init__(self, model):
        self.model = model

    @property
    def PropertyChanged(self):
        return self

    @PropertyChanged.setter
    def PropertyChanged(self, value):
        pass

    def __iadd__(self, handler):
        self.model.handlers.append(handler)
        return self


def _load_binding():
    system = SimpleNamespace(
        IO=SimpleNamespace(FileNotFoundException=OSError),
        String=str,
        Object=object,
    )
    framework = ModuleType("pyrevit.framework")
    framework.System = system
    framework.ComponentModel = SimpleNamespace(
        PropertyChangedEventArgs=lambda name: SimpleNamespace(PropertyName=name),
        INotifyPropertyChanged=_Notifier,
    )
    framework.to_clr_list = lambda kind, values: list(values)
    dynamic = ModuleType("System.Dynamic")
    dynamic.ExpandoObject = _Expando
    generic = ModuleType("System.Collections.Generic")
    generic.IDictionary = {(str, object): lambda model: model}
    clr = ModuleType("clr")
    clr.AddReference = lambda name: None
    stubs = {
        "clr": clr,
        "pyrevit.framework": framework,
        "System": ModuleType("System"),
        "System.Dynamic": dynamic,
        "System.Collections": ModuleType("System.Collections"),
        "System.Collections.Generic": generic,
    }
    with mock.patch.dict(sys.modules, stubs):
        spec = importlib.util.spec_from_file_location(
            "forms_binding", FORMS / "backends" / "_binding.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


class BindingRefreshTests(unittest.TestCase):
    """Copy only the values a binding change can affect."""

    def setUp(self):
        """Build a model with a form base property and tracked getters."""
        self.binding = _load_binding()
        self.reads = []
        reads = self.reads

        def tracked(name):
            def get(self):
                reads.append(name)
                return self.__dict__.get("_" + name, name)

            def set(self, value):
                self.__dict__["_" + name] = value
                self.OnPropertyChanged("summary")

            return property(get, set)

        infrastructure = type(
            "WPFWindow",
            (object,),
            {"_binding_exclude": True, "pyrevit_version": tracked("ver")},
        )
        self.Model = type(
            "Model",
            (infrastructure, self.binding.Reactive),
            {"title": tracked("title"), "summary": tracked("summary")},
        )

    def test_form_infrastructure_and_named_controls_are_not_copied(self):
        """Form base properties and XAML names never reach the binding model."""
        model = self.Model()
        model.__dict__["_xaml_names"] = frozenset(["okButton"])
        model.okButton = object()
        model.count = 1
        native = self.binding.binding_source(model)
        self.assertEqual({"title", "summary", "count"}, set(native.values))
        self.assertNotIn("ver", self.reads)

    def test_rebinding_refreshes_own_properties_but_not_infrastructure(self):
        """Rebinding re-reads the model's own properties and plain attributes."""
        model = self.Model()
        model.count = 1
        native = self.binding.binding_source(model)
        del self.reads[:]
        model.count = 2
        model.__dict__["_title"] = "changed"
        self.assertIs(native, self.binding.binding_source(model))
        self.assertEqual(2, native["count"])
        self.assertEqual("changed", native["title"])
        self.assertEqual(["summary", "title"], sorted(self.reads))

    def test_rebinding_refreshes_computed_list_item_properties(self):
        """Read-only properties backed by private state are current after rebind."""

        class Item(self.binding.Reactive):
            def __init__(self):
                self._checkable = True

            @property
            def checkable(self):
                return "Visible" if self._checkable else "Collapsed"

        item = Item()
        native = self.binding.binding_source(item)
        item._checkable = False
        self.binding.binding_source(item)
        self.assertEqual("Collapsed", native["checkable"])

    def test_subclasses_of_excluded_classes_contribute_their_properties(self):
        """The exclusion marker applies only to the class that declares it."""

        class Excluded(self.binding.Reactive):
            _binding_exclude = True

            @property
            def use_regex(self):
                return True

        class Custom(Excluded):
            @property
            def label(self):
                return "custom"

        native = self.binding.binding_source(Custom())
        self.assertEqual({"label"}, set(native.values))

    def test_two_way_edit_refreshes_only_written_and_notified_names(self):
        """A WPF edit re-reads the edited property and what its setter notified."""
        model = self.Model()
        native = self.binding.binding_source(model)
        del self.reads[:]
        native.edit("title", "new")
        self.assertEqual(["summary", "title"], self.reads)
        self.assertEqual("new", model.title)

    def test_two_way_edit_copies_plain_attributes_the_setter_changed(self):
        """A setter's side effect on a plain attribute reaches WPF too."""

        class Item(self.binding.Reactive):
            def __init__(self):
                self.state = False
                self.untouched = "same"

            @property
            def checked(self):
                return self.state

            @checked.setter
            def checked(self, value):
                self.state = value

        item = Item()
        native = self.binding.binding_source(item)
        native.edit("checked", True)
        self.assertTrue(item.state)
        self.assertTrue(native["state"])
        self.assertEqual("same", native["untouched"])


class FormsExportsTests(unittest.TestCase):
    """Keep accidental legacy exports compatible as well as the intended API."""

    def test_ironpython_public_names_match_the_pre_extraction_surface(self):
        """IronPython keeps every pre-split name; additions are listed explicitly."""
        fixture = Path(__file__).parent / "fixtures" / "forms_ironpython_exports.json"
        pre_split = json.loads(fixture.read_text(encoding="utf-8"))
        intended_additions = {"warning", "set_data_context"}
        common = _literal_list(FORMS / "_common.py", "__all__")
        legacy = _literal_list(FORMS / "_legacy_exports.py", "LEGACY_EXPORTS")
        self.assertFalse(set(common) & set(legacy))
        self.assertFalse(set(pre_split) & intended_additions)
        self.assertEqual(
            sorted(pre_split) + sorted(intended_additions),
            sorted(set(common + legacy) - intended_additions)
            + sorted(intended_additions),
        )
        self.assertFalse(set(legacy) - _defined_names(FORMS / "_ipy_legacy.py"))

    def test_shared_names_are_defined_by_the_shared_module(self):
        """Every engine-neutral export resolves without engine-specific code."""
        common = _literal_list(FORMS / "_common.py", "__all__")
        self.assertFalse(set(common) - _defined_names(FORMS / "_common.py"))

    def test_both_backends_implement_the_backend_contract(self):
        """Feature modules can rely on every _backend name under either engine."""
        contract = _literal_list(FORMS / "_backend.py", "__all__")
        for backend in ("_ipy.py", "_cpy.py"):
            with self.subTest(backend=backend):
                defined = _defined_names(FORMS / "backends" / backend)
                self.assertFalse(set(contract) - defined)


def _literal_list(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return ast.literal_eval(
        next(
            node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets
            )
        )
    )


def _defined_names(path):
    defined = set()
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
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
    return defined


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

    def test_unknown_value_type_is_rejected_before_the_window_exists(self):
        """Both engines refuse an input mode that would open an empty dialog."""
        dialog_class = _load_dialog_class()
        del _InputWindow.created[:]
        with self.assertRaises(_PyRevitException):
            dialog_class(None, "Title", 400, 300, value_type="color")
        self.assertEqual([], _InputWindow.created)
        dialog_class(None, "Title", 400, 300, value_type="slider")
        self.assertEqual([{"value_type": "slider"}], _InputWindow.created)

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
