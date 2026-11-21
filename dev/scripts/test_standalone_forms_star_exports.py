"""Check what ``from pyrevit.forms import *`` exports, without Revit.

Both engines build the star-import list from literal lists, so the tests read
them with ``ast`` instead of importing the forms package.
"""

import ast
import importlib.util
from pathlib import Path
import unittest


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

ROOT = Path(__file__).resolve().parents[2]
FORMS = ROOT / "pyrevitlib" / "pyrevit" / "forms"
ATTRIBUTE_ONLY = {"warning", "set_data_context"}


def _parse(path):
    return ast.parse(path.read_text(encoding="utf-8-sig"))


def _literal_list(path, name):
    for node in _parse(path).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("{} has no literal {}".format(path, name))


def _forms_references_in_extensions():
    spec = importlib.util.spec_from_file_location(
        "forms_usage", Path(__file__).resolve().with_name("forms_usage.py")
    )
    usage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(usage)
    names = set()
    unparsable = []
    for path in (ROOT / "extensions").rglob("*.py"):
        try:
            names |= usage.forms_references(_parse(path))
        except (SyntaxError, UnicodeError):
            unparsable.append(str(path.relative_to(ROOT)))
    return names, unparsable


def _is_submodule(name):
    return (FORMS / (name + ".py")).exists() or (FORMS / name).is_dir()


class StarExportTests(unittest.TestCase):
    """Keep the star import free of names that shadow user code."""

    @classmethod
    def setUpClass(cls):
        """Read the CPython and IronPython star-import lists."""
        common = _literal_list(FORMS / "_common.py", "__all__")
        legacy = _literal_list(FORMS / "_legacy_exports.py", "LEGACY_EXPORTS")
        cls.star_lists = {"cpython": common, "ironpython": common + legacy}

    def test_star_import_excludes_attribute_only_names(self):
        """``warning`` and ``set_data_context`` are not star-imported."""
        for engine, exported in self.star_lists.items():
            with self.subTest(engine=engine):
                self.assertFalse(ATTRIBUTE_ONLY & set(exported))

    def test_star_import_keeps_the_api_bundled_extensions_use(self):
        """Every other ``pyrevit.forms`` name the extensions use is exported."""
        references, unparsable = _forms_references_in_extensions()
        self.assertEqual(unparsable, [])
        used = {name for name in references - ATTRIBUTE_ONLY if not _is_submodule(name)}
        self.assertIn("alert", used)
        for engine, exported in self.star_lists.items():
            with self.subTest(engine=engine):
                self.assertFalse(used - set(exported))

    def test_attribute_only_names_stay_module_attributes(self):
        """The facade imports both names from ``_common`` for every engine."""
        imported = set()
        for node in _parse(FORMS / "__init__.py").body:
            if (
                isinstance(node, ast.ImportFrom)
                and node.level == 1
                and node.module == "_common"
            ):
                imported.update(item.name for item in node.names)
        self.assertLessEqual(ATTRIBUTE_ONLY, imported)

    def test_attribute_only_names_are_imported_by_the_shared_module(self):
        """``_common`` still binds both names, so the facade import resolves."""
        bound = set()
        for node in _parse(FORMS / "_common.py").body:
            if isinstance(node, ast.ImportFrom):
                bound.update(item.asname or item.name for item in node.names)
        self.assertLessEqual(ATTRIBUTE_ONLY, bound)


if __name__ == "__main__":
    unittest.main()
