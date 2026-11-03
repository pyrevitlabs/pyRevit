"""Exercise the extension catalog validator used by the catalog workflows."""

import copy
import importlib.util
import json
import os
import unittest

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPTS_DIR))


def _load_checker():
    spec = importlib.util.spec_from_file_location(
        "_test_check_extension_catalog",
        os.path.join(SCRIPTS_DIR, "check_extension_catalog.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALID_ENTRY = {
    "builtin": "False",
    "type": "extension",
    "rocket_mode_compatible": "True",
    "name": "Sample",
    "description": "Sample extension",
    "author": "Someone",
    "url": "https://github.com/someone/sample.git",
    "website": "https://github.com/someone/sample",
    "image": "",
    "dependencies": [],
}


class CheckExtensionCatalogTests(unittest.TestCase):
    """The validator accepts the shipped catalog and rejects broken entries."""

    @classmethod
    def setUpClass(cls):
        cls.checker = _load_checker()

    def _problems(self, *entries):
        return self.checker.check_catalog({"extensions": list(entries)})

    def _entry(self, **overrides):
        entry = copy.deepcopy(VALID_ENTRY)
        entry.update(overrides)
        return entry

    def test_shipped_catalog_is_valid(self):
        path = os.path.join(REPO_ROOT, "extensions", "extensions.json")
        with open(path, encoding="utf-8") as catalog:
            self.assertEqual(self.checker.check_catalog(json.load(catalog)), [])

    def test_valid_entry_passes(self):
        self.assertEqual(self._problems(self._entry()), [])

    def test_catalog_without_extensions_list_fails(self):
        self.assertTrue(self.checker.check_catalog({"extensions": {}}))
        self.assertTrue(self.checker.check_catalog([]))

    def test_missing_required_field_fails(self):
        entry = self._entry()
        del entry["url"]
        self.assertIn("entry #0 (Sample): missing 'url'", self._problems(entry))

    def test_non_https_install_url_fails(self):
        problems = self._problems(self._entry(url="http://example.com/a.git"))
        self.assertIn("entry #0 (Sample): 'url' must start with https://", problems)

    def test_http_website_is_allowed(self):
        self.assertEqual(self._problems(self._entry(website="http://example.com")), [])

    def test_unknown_type_fails(self):
        self.assertTrue(self._problems(self._entry(type="plugin")))

    def test_boolean_fields_must_be_strings(self):
        self.assertTrue(self._problems(self._entry(builtin=False)))
        self.assertTrue(self._problems(self._entry(rocket_mode_compatible="yes")))

    def test_list_fields_must_hold_names(self):
        self.assertTrue(self._problems(self._entry(authusers="someone")))
        self.assertTrue(self._problems(self._entry(dependencies=5)))

    def test_link_fields_must_be_strings(self):
        self.assertTrue(self._problems(self._entry(website=0)))
        self.assertTrue(self._problems(self._entry(image=["a"])))

    def test_duplicate_names_fail_case_insensitively(self):
        problems = self._problems(self._entry(), self._entry(name="sample"))
        self.assertIn("duplicate name 'sample' (also 'Sample')", problems)

    def test_unknown_dependency_fails(self):
        problems = self._problems(self._entry(dependencies=["Missing"]))
        self.assertIn("Sample: dependency 'Missing' is not in the catalog", problems)

    def test_known_dependency_passes(self):
        library = self._entry(name="Lib", type="lib")
        self.assertEqual(self._problems(library, self._entry(dependencies=["Lib"])), [])


if __name__ == "__main__":
    unittest.main()
