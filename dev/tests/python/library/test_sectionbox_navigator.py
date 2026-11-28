"""Host-free tests for the Section Box Navigator's lookups and strings.

Covers which design option, phase and detail level the 3D preview follows,
which level a box edge sits on, and that every language file has the same
strings. The Revit modules are loaded with a stubbed ``pyrevit``.
"""

import importlib.util
import pathlib
import re
import sys
import types
import unittest
import xml.dom.minidom

import pytest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

BUNDLE = (
    pathlib.Path(__file__).resolve().parents[4]
    / "extensions"
    / "pyRevitTools.extension"
    / "pyRevit.tab"
    / "Modify.panel"
    / "3D.pulldown"
    / "Section Box Navigator.pushbutton"
)
LOCALES = (
    "chinese_s",
    "de_de",
    "en_us",
    "es_es",
    "fr_fr",
    "ko",
    "pt_br",
    "ru",
)


def load_with_stubs(filename):
    pyrevit = types.ModuleType("pyrevit")
    pyrevit.DB = types.SimpleNamespace()
    compat = types.ModuleType("pyrevit.compat")
    compat.get_elementid_value_func = lambda: int
    framework = types.ModuleType("pyrevit.framework")
    framework.List = list
    revit = types.ModuleType("pyrevit.revit")
    revit.geom = None
    stubs = {
        "pyrevit": pyrevit,
        "pyrevit.compat": compat,
        "pyrevit.framework": framework,
        "pyrevit.revit": revit,
    }
    previous = dict((name, sys.modules.get(name)) for name in stubs)
    sys.modules.update(stubs)
    try:
        spec = importlib.util.spec_from_file_location(
            filename + "_under_test", BUNDLE / (filename + ".py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name, original in previous.items():
            if original is None:
                del sys.modules[name]
            else:
                sys.modules[name] = original
    return module


class ShownDesignOptionTests(unittest.TestCase):
    OPTIONS = [
        (11, 1, True),
        (12, 1, False),
        (13, 1, False),
        (21, 2, True),
        (22, 2, False),
    ]

    @classmethod
    def setUpClass(cls):
        cls.choose = staticmethod(
            load_with_stubs("sectionbox_scene_filter").choose_shown_options
        )

    def test_each_set_shows_its_primary_option(self):
        self.assertEqual(self.choose(self.OPTIONS), [11, 21])

    def test_the_view_option_replaces_the_primary_of_its_set_only(self):
        self.assertEqual(self.choose(self.OPTIONS, view_option_id=12), [12, 21])

    def test_the_option_being_edited_wins_over_the_view_option(self):
        self.assertEqual(
            self.choose(self.OPTIONS, active_id=13, view_option_id=12), [13, 21]
        )
        self.assertEqual(
            self.choose(self.OPTIONS, active_id=22, view_option_id=12), [12, 22]
        )

    def test_the_result_does_not_depend_on_the_order_of_the_options(self):
        self.assertEqual(
            self.choose(list(reversed(self.OPTIONS)), active_id=13), [13, 21]
        )


class FollowedViewTests(unittest.TestCase):
    PHASE, FILTER = 5, 6

    def follow(self, filter_id, hidden=(), detail_level="Medium"):
        module = load_with_stubs("sectionbox_scene_filter")
        db = module.DB
        db.ViewDetailLevel = types.SimpleNamespace(
            Undefined="Undefined", Coarse="Coarse", Medium="Medium", Fine="Fine"
        )
        db.ElementId = types.SimpleNamespace(InvalidElementId=-1)
        db.BuiltInParameter = types.SimpleNamespace(
            VIEW_PHASE="phase",
            VIEW_PHASE_FILTER="phase_filter",
            VIEWER_OPTION_VISIBILITY="option",
        )
        db.DesignOption = types.SimpleNamespace(GetActiveDesignOptionId=lambda doc: -1)
        db.ElementOnPhaseStatus = types.SimpleNamespace(
            **dict((name, name) for name in module.PHASE_STATUS_NAMES)
        )
        db.PhaseStatusPresentation = types.SimpleNamespace(DontShow="hidden")
        phase_filter = types.SimpleNamespace(
            GetPhaseStatusPresentation=lambda status: (
                "hidden" if status in hidden else "shown"
            )
        )
        values = {"phase": self.PHASE, "phase_filter": filter_id, "option": -1}
        view = types.SimpleNamespace(
            DetailLevel=detail_level,
            Document=types.SimpleNamespace(GetElement=lambda _: phase_filter),
            get_Parameter=lambda name: types.SimpleNamespace(
                AsElementId=lambda: values[name]
            ),
        )
        return module.SceneFilter.for_view(view)

    def test_a_named_phase_filter_limits_the_phase_statuses(self):
        followed = self.follow(self.FILTER, hidden=("Demolished", "Temporary"))
        self.assertEqual(followed.phase_id, self.PHASE)
        self.assertEqual(followed.statuses, ("Existing", "New"))

    def test_the_phase_filter_none_shows_elements_of_every_phase(self):
        """Revit shows later phases too, which a status filter would leave out."""
        followed = self.follow(-1)
        self.assertEqual((followed.phase_id, followed.statuses), (None, ()))

    @pytest.mark.regression
    def test_the_view_detail_level_is_followed(self):
        """Fittings stayed missing in Fine views: discourse.pyrevitlabs.io/t/10788/7."""
        for level in ("Coarse", "Medium", "Fine"):
            with self.subTest(level=level):
                self.assertEqual(
                    self.follow(-1, detail_level=level).detail_level, level
                )
        self.assertEqual(
            self.follow(-1, detail_level="Undefined").detail_level, "Medium"
        )

    def test_another_detail_level_streams_the_model_again(self):
        self.assertNotEqual(
            self.follow(-1, detail_level="Medium").key,
            self.follow(-1, detail_level="Fine").key,
        )


class LevelAtElevationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.navigation = load_with_stubs("sectionbox_navigation")

    def level(self, name, elevation, link=False):
        level = types.SimpleNamespace(Name=name, ProjectElevation=elevation)
        if link:
            level.SourceLink = object()
        return level

    def name_at(self, elevation, levels):
        level = self.navigation.get_level_at(elevation, levels, 1e-5)
        return level.Name if level else None

    def test_the_level_the_next_above_and_below_skip_is_the_one_named(self):
        levels = [self.level("L1", 0.0), self.level("L2", 10.0)]
        self.assertEqual(self.name_at(10.000001, levels), "L2")
        self.assertIsNone(self.name_at(10.001, levels))
        above = self.navigation.get_next_level_above(10.000001, levels, 1e-5)
        below = self.navigation.get_next_level_below(10.000001, levels, 1e-5)
        self.assertEqual((above[0], below[0].Name), (None, "L1"))

    def test_a_host_level_wins_over_a_linked_one(self):
        levels = [self.level("Linked", 0.0, link=True), self.level("Host", 0.0)]
        self.assertEqual(self.name_at(0.0, levels), "Host")
        self.assertEqual(self.name_at(0.0, levels[:1]), "Linked")


class LocaleTests(unittest.TestCase):
    def strings(self, locale):
        path = BUNDLE / "SectionBoxNavigator.ResourceDictionary.{}.xaml".format(locale)
        document = xml.dom.minidom.parse(str(path))
        return dict(
            (
                node.getAttribute("x:Key"),
                "".join(child.data for child in node.childNodes),
            )
            for node in document.getElementsByTagName("system:String")
        )

    def test_every_language_has_the_same_strings_with_the_same_placeholders(self):
        def placeholders(text):
            return sorted(set(re.findall(r"\{\d+\}", text)))

        english = self.strings("en_us")
        for locale in LOCALES:
            with self.subTest(locale=locale):
                strings = self.strings(locale)
                self.assertEqual(sorted(strings), sorted(english))
                for key, text in strings.items():
                    self.assertEqual(
                        placeholders(text), placeholders(english[key]), key
                    )

    def test_every_string_the_preview_page_asks_for_exists(self):
        source = (BUNDLE / "sectionbox_preview.py").read_text(encoding="utf-8")
        block = source.split("PAGE_STRINGS = (", 1)[1].split(")", 1)[0]
        sent = set(re.findall(r'"(\w+)"', block))
        page = (BUNDLE / "preview.js").read_text(encoding="utf-8")
        asked = set(re.findall(r'"(Preview[A-Z]\w+)"', page))
        self.assertEqual(sorted(asked - sent), [])
        self.assertEqual(sorted(sent - set(self.strings("en_us"))), [])


if __name__ == "__main__":
    unittest.main()
