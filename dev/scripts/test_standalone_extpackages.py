"""Exercise extension load-state resolution without a Revit host."""

import importlib.util
import json
import logging
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PYREVIT_ROOT = os.path.join(REPO_ROOT, "pyrevitlib", "pyrevit")
DEFAULT_CATALOG_URL = (
    "https://github.com/pyrevitlabs/pyRevit/raw/master/extensions/extensions.json"
)


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Configuration:
    def __init__(self):
        self.sections = {}

    def HasSection(self, name):
        return name in self.sections

    def AddSection(self, name):
        self.sections.setdefault(name, {})

    def HasSectionKey(self, name, key):
        return key in self.sections[name]

    def GetRawValueOrDefault(self, name, key, default=None):
        return self.sections[name].get(key, default)

    def SetRawValue(self, name, key, value):
        self.sections[name][key] = value


def _load_extpackages():
    pyrevit = types.ModuleType("pyrevit")
    pyrevit.PyRevitException = Exception
    pyrevit.HOST_APP = types.SimpleNamespace(username="test-user")
    pyrevit.PYREVIT_APP_DIR = tempfile.gettempdir()
    pyrevit.labs = types.ModuleType("pyrevit.labs")
    pyrevit.labs.PyRevit = types.SimpleNamespace(
        PyRevitConsts=types.SimpleNamespace(
            ExtensionsDefinitionFileUri=DEFAULT_CATALOG_URL
        )
    )
    coreutils = types.ModuleType("pyrevit.coreutils")
    coreutils.git = types.SimpleNamespace()
    coreutils.fully_remove_dir = lambda path: None
    logger = types.ModuleType("pyrevit.coreutils.logger")
    logger.get_logger = logging.getLogger
    compat = types.ModuleType("pyrevit.compat")
    compat.safe_strtype = str
    extensions = types.ModuleType("pyrevit.extensions")
    ui_extension = types.SimpleNamespace(ID="extension", POSTFIX=".extension")
    lib_extension = types.SimpleNamespace(ID="lib", POSTFIX=".lib")
    extensions.ExtensionTypes = types.SimpleNamespace(
        UI_EXTENSION=ui_extension,
        get_ext_types=lambda: [ui_extension, lib_extension],
    )
    extensions.JSON_FILE_FORMAT = ".json"
    pyrevit.extensions = extensions
    userconfig = types.ModuleType("pyrevit.userconfig")
    userconfig.user_config = None
    modules = {
        "pyrevit": pyrevit,
        "pyrevit.compat": compat,
        "pyrevit.coreutils": coreutils,
        "pyrevit.coreutils.logger": logger,
        "pyrevit.extensions": extensions,
        "pyrevit.userconfig": userconfig,
    }
    with patch.dict(sys.modules, modules):
        configparser = _load_module(
            "_test_configparser",
            os.path.join(PYREVIT_ROOT, "coreutils", "configparser.py"),
        )
        extcatalog = _load_module(
            "_test_extcatalog",
            os.path.join(PYREVIT_ROOT, "extensions", "extcatalog.py"),
        )
        extensions.extcatalog = extcatalog
        sys.modules["pyrevit.extensions.extcatalog"] = extcatalog
        extpackages = _load_module(
            "_test_extpackages",
            os.path.join(PYREVIT_ROOT, "extensions", "extpackages.py"),
        )
    return extpackages, configparser


class ExtensionPackageLoadStateTests(unittest.TestCase):
    """Load state resolves the manifest default when no choice is stored."""

    @classmethod
    def setUpClass(cls):
        """Load production modules with only host dependencies replaced."""
        cls.extpackages, cls.configparser = _load_extpackages()

    def setUp(self):
        """Isolate settings and capture snapshots at each persistence boundary."""
        self.backend = _Configuration()
        self.sections = self.configparser.ConfigSections(
            types.SimpleNamespace(Configuration=self.backend)
        )
        self.saved = []
        user_config = types.SimpleNamespace(
            has_section=self.sections.has_section,
            get_section=self.sections.get_section,
            add_section=self.sections.add_section,
            save_changes=lambda: self.saved.append(
                json.loads(json.dumps(self.backend.sections))
            ),
            get_ext_root_dirs=lambda: [],
        )
        self.config_patch = patch.object(self.extpackages, "user_config", user_config)
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)
        self.package = self.extpackages.ExtensionPackage(
            {"name": "Example", "url": "https://example.com/example.git"}
        )

    def _assert_nothing_written(self, before):
        self.assertEqual([], self.saved)
        self.assertEqual(before, self.backend.sections)

    def _credential_only_section(self):
        config = self.sections.add_section("Example.extension")
        config.credential = "sealed-test-credential"
        return json.loads(json.dumps(self.backend.sections))

    def test_absent_section_uses_manifest_default(self):
        """No section at all: the manifest default decides and nothing is created."""
        self.assertTrue(self.package.is_enabled)
        self.package.default_enabled = False
        self.assertFalse(self.package.is_enabled)

        self._assert_nothing_written({})

    def test_credential_only_section_honours_opt_out_manifest(self):
        """A section created by storing a credential is not an explicit enable."""
        before = self._credential_only_section()
        self.package.default_enabled = False

        self.assertFalse(self.package.is_enabled)
        self._assert_nothing_written(before)

    def test_credential_only_section_honours_default_manifest(self):
        """Reading the load state must not raise when the key is absent."""
        before = self._credential_only_section()

        self.assertTrue(self.package.is_enabled)
        self._assert_nothing_written(before)

    def test_explicit_disable_wins_over_manifest(self):
        """An explicit disabled=true is honoured regardless of the manifest."""
        self.sections.add_section("Example.extension").disabled = True
        before = json.loads(json.dumps(self.backend.sections))

        self.assertFalse(self.package.is_enabled)
        self._assert_nothing_written(before)

    def test_explicit_enable_wins_over_manifest(self):
        """An explicit disabled=false is honoured regardless of the manifest."""
        self.sections.add_section("Example.extension").disabled = False
        before = json.loads(json.dumps(self.backend.sections))
        self.package.default_enabled = False

        self.assertTrue(self.package.is_enabled)
        self._assert_nothing_written(before)

    def test_config_access_seeds_nothing(self):
        """The write path creates the section but persists no defaults."""
        self.package.default_enabled = False
        self.package.builtin = True

        config = self.package.config

        self.assertFalse(config.has_option("disabled"))
        self.assertFalse(config.has_option("private_repo"))
        self.assertEqual([], self.saved)

    def test_toggle_from_manifest_default_stores_explicit_choice(self):
        """Toggling an opt-out package with no stored choice enables it."""
        before = self._credential_only_section()
        self.package.default_enabled = False

        self.package.toggle_package()

        section = self.backend.sections["Example.extension"]
        self.assertEqual("false", section["disabled"])
        self.assertEqual(
            before["Example.extension"]["credential"], section["credential"]
        )
        self.assertNotIn("private_repo", section)
        self.assertTrue(self.package.is_enabled)
        self.assertEqual(1, len(self.saved))


def _catalog_text(*names, **urls):
    return json.dumps(
        {
            "extensions": [
                {
                    "name": name,
                    "type": "extension",
                    "url": urls.get(name, "https://example.com/{}.git".format(name)),
                }
                for name in names
            ]
        }
    )


class ExtensionCatalogResolveTests(unittest.TestCase):
    """Remote catalogs are cached, validated and never break the manager."""

    @classmethod
    def setUpClass(cls):
        """Load the catalog module with host dependencies replaced."""
        extpackages, _ = _load_extpackages()
        cls.extcatalog = extpackages.extcatalog

    def setUp(self):
        """Give each test an empty cache and a fresh failure memory."""
        self.cache_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.cache_dir, True))
        self.extcatalog._last_failure_time.clear()
        self.calls = []
        self.url = DEFAULT_CATALOG_URL

    def _download(self, text):
        def download(url, timeout_ms):
            self.calls.append(url)
            if isinstance(text, Exception):
                raise text
            return text

        return download

    def _resolve(self, text, now, force=False):
        return self.extcatalog.resolve(
            self.url,
            self.cache_dir,
            download=self._download(text),
            now=now,
            force=force,
        )

    def _cached_names(self, path):
        with open(path, encoding="utf-8") as cached:
            return [e["name"] for e in json.load(cached)["extensions"]]

    def test_download_is_cached(self):
        """A good download is written to the cache and returned."""
        path = self._resolve(_catalog_text("A"), now=1000.0)
        self.assertEqual(["A"], self._cached_names(path))

    def test_fresh_cache_skips_download(self):
        """A cache younger than the TTL is used without a network call."""
        path = self._resolve(_catalog_text("A"), now=None)
        self.calls.clear()
        self.assertEqual(path, self._resolve(_catalog_text("B"), now=None))
        self.assertEqual([], self.calls)

    def test_failed_download_keeps_stale_cache(self):
        """Offline: the last good copy is returned, not None."""
        path = self._resolve(_catalog_text("A"), now=None)
        stale = self._resolve(IOError("offline"), now=None, force=True)
        self.assertEqual(path, stale)
        self.assertEqual(["A"], self._cached_names(stale))

    def test_failure_without_cache_returns_none(self):
        """No copy at all: the caller falls back to the bundled catalog."""
        self.assertIsNone(self._resolve(IOError("offline"), now=1000.0))

    def test_failure_is_not_retried_immediately(self):
        """An offline session does not wait on every catalog read."""
        self._resolve(IOError("offline"), now=1000.0)
        self._resolve(IOError("offline"), now=1001.0)
        self.assertEqual(1, len(self.calls))
        retry_at = 1000.0 + self.extcatalog.RETRY_AFTER_FAILURE_SECONDS
        self._resolve(IOError("offline"), now=retry_at)
        self.assertEqual(2, len(self.calls))

    def test_invalid_catalog_does_not_replace_cache(self):
        """A broken publish never overwrites the last good copy."""
        path = self._resolve(_catalog_text("A"), now=None)
        self._resolve("<html>not json</html>", now=None, force=True)
        self._resolve(json.dumps({"extensions": []}), now=None, force=True)
        self.assertEqual(["A"], self._cached_names(path))

    def test_entries_without_https_url_are_dropped(self):
        """Only https install URLs reach the Extension Manager."""
        text = _catalog_text("A", "B", B="http://example.com/b.git")
        self.assertEqual(["A"], self._cached_names(self._resolve(text, now=1000.0)))

    def test_entries_with_wrong_field_types_are_dropped(self):
        """Entries ExtensionPackage could not consume never reach the cache."""
        catalog = json.loads(_catalog_text("Good", "Deps", "Auth", "Flag", "Text"))
        catalog["extensions"][1]["dependencies"] = 5
        catalog["extensions"][2]["authusers"] = [1]
        catalog["extensions"][3]["builtin"] = ["True"]
        catalog["extensions"][4]["description"] = {"en": "x"}
        path = self._resolve(json.dumps(catalog), now=1000.0)
        self.assertEqual(["Good"], self._cached_names(path))

    def test_cache_write_leaves_no_temp_file(self):
        """Each write uses its own temp file and swaps it in whole."""
        self._resolve(_catalog_text("A"), now=1000.0)
        self._resolve(_catalog_text("B"), now=1000.0, force=True)
        self.assertEqual(1, len(os.listdir(self.cache_dir)))

    def test_cache_folder_created_concurrently_is_tolerated(self):
        """Another session creating the cache folder first is not an error."""
        folder = os.path.join(self.cache_dir, "new")
        real_makedirs = os.makedirs

        def makedirs_after_other_session(path):
            real_makedirs(path)
            raise OSError(17, "File exists")

        with patch.object(self.extcatalog.os, "makedirs", makedirs_after_other_session):
            self.extcatalog._ensure_folder(folder)
        self.assertTrue(os.path.isdir(folder))

    def test_cache_folder_error_is_raised(self):
        """A real failure to create the folder still surfaces."""
        folder = os.path.join(self.cache_dir, "denied")
        with patch.object(
            self.extcatalog.os, "makedirs", side_effect=OSError(13, "Access denied")
        ):
            with self.assertRaises(OSError):
                self.extcatalog._ensure_folder(folder)

    def test_cache_only_mode_never_downloads(self):
        """allow_download=False returns even a stale cache, offline."""
        path = self._resolve(_catalog_text("A"), now=1000.0)
        self.calls.clear()
        later = 1000.0 + 10 * self.extcatalog.CACHE_TTL_SECONDS
        cached = self.extcatalog.resolve(
            self.url,
            self.cache_dir,
            download=self._download(_catalog_text("B")),
            now=later,
            allow_download=False,
        )
        self.assertEqual(path, cached)
        self.assertEqual([], self.calls)

    def test_non_https_catalog_url_is_ignored(self):
        """A plain-http catalog is never downloaded."""
        self.url = "http://example.com/extensions.json"
        self.assertIsNone(self._resolve(_catalog_text("A"), now=1000.0))
        self.assertEqual([], self.calls)

    def test_remote_source_detection(self):
        """URLs are remote sources, file paths are not."""
        self.assertTrue(self.extcatalog.is_remote_source("HTTPS://example.com/x.json"))
        self.assertFalse(self.extcatalog.is_remote_source(r"C:\\catalogs\\x.json"))
        self.assertFalse(self.extcatalog.is_remote_source(None))


class _FakeUri:
    def __init__(self, base, relative=None):
        from urllib.parse import urljoin, urlsplit

        self.text = urljoin(str(base), relative) if relative else str(base)
        self.Scheme = urlsplit(self.text).scheme

    def __str__(self):
        return self.text


class _FakeResponse:
    def __init__(self, status, location=None):
        self.StatusCode = status
        self.Headers = {"Location": location}
        self.closed = False

    def Close(self):
        self.closed = True


class _FakeWeb:
    """Stands in for `pyrevit.framework`, serving a fixed redirect table."""

    def __init__(self, routes):
        self.routes = routes
        self.requested = []
        self.Uri = _FakeUri
        self.WebRequest = types.SimpleNamespace(Create=self._create)

    def _create(self, uri):
        web = self
        request = types.SimpleNamespace()

        def get_response():
            web.requested.append((str(uri), request.AllowAutoRedirect))
            status, location = web.routes[str(uri)]
            return _FakeResponse(status, location)

        request.GetResponse = get_response
        return request


class ExtensionCatalogRedirectTests(unittest.TestCase):
    """Every redirect hop is checked before it is followed."""

    @classmethod
    def setUpClass(cls):
        """Load the catalog module with host dependencies replaced."""
        extpackages, _ = _load_extpackages()
        cls.extcatalog = extpackages.extcatalog

    def _open(self, routes, url="https://a.example/x.json", elapsed_ms=0):
        web = _FakeWeb(routes)
        stopwatch = types.SimpleNamespace(ElapsedMilliseconds=elapsed_ms)
        response = self.extcatalog._open_following_https_redirects(
            web, url, 1000, stopwatch
        )
        return web, response

    def test_https_redirects_are_followed(self):
        """A GitHub-style https redirect reaches the catalog."""
        web, response = self._open(
            {
                "https://a.example/x.json": (302, "https://b.example/x.json"),
                "https://b.example/x.json": (200, None),
            }
        )
        self.assertEqual(200, response.StatusCode)
        self.assertEqual([False, False], [auto for _, auto in web.requested])

    def test_relative_redirect_is_resolved(self):
        """A relative Location stays on the same https host."""
        web, _ = self._open(
            {
                "https://a.example/x.json": (301, "/y.json"),
                "https://a.example/y.json": (200, None),
            }
        )
        self.assertEqual("https://a.example/y.json", web.requested[-1][0])

    def test_http_hop_is_refused_before_request(self):
        """https -> http -> https fails without ever requesting the http hop."""
        routes = {
            "https://a.example/x.json": (302, "http://b.example/x.json"),
            "http://b.example/x.json": (302, "https://c.example/x.json"),
        }
        web = _FakeWeb(routes)
        stopwatch = types.SimpleNamespace(ElapsedMilliseconds=0)
        with self.assertRaises(self.extcatalog.CatalogError):
            self.extcatalog._open_following_https_redirects(
                web, "https://a.example/x.json", 1000, stopwatch
            )
        self.assertEqual(["https://a.example/x.json"], [u for u, _ in web.requested])

    def test_non_success_status_is_refused(self):
        """A 300 or other non-2xx answer is never treated as the catalog."""
        with self.assertRaises(self.extcatalog.CatalogError):
            self._open({"https://a.example/x.json": (300, None)})

    def test_spent_time_budget_stops_before_request(self):
        """Redirects cannot stretch the wait past MAX_DOWNLOAD_MS."""
        with self.assertRaises(self.extcatalog.CatalogError):
            self._open(
                {"https://a.example/x.json": (200, None)},
                elapsed_ms=self.extcatalog.MAX_DOWNLOAD_MS,
            )

    def test_redirect_loop_is_bounded(self):
        """A redirect loop stops after MAX_REDIRECTS hops."""
        routes = {"https://a.example/x.json": (302, "https://a.example/x.json")}
        with self.assertRaises(self.extcatalog.CatalogError):
            self._open(routes)


class ExtensionCatalogSourcesTests(unittest.TestCase):
    """The Extension Manager merges bundled, hosted and user catalogs."""

    @classmethod
    def setUpClass(cls):
        """Load production modules with only host dependencies replaced."""
        cls.extpackages, _ = _load_extpackages()

    def setUp(self):
        """Point the bundled catalog and the cache at temporary folders."""
        self.root = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.root, True))
        self.ext_dir = os.path.join(self.root, "extensions")
        os.makedirs(self.ext_dir)
        self._write(os.path.join(self.ext_dir, "extensions.json"), "Bundled", "Shared")
        self.options = {}
        self.sources = []
        self.resolved = []
        self.downloads_allowed = []
        core = types.SimpleNamespace(
            get_option=lambda name, default=None: self.options.get(name, default)
        )
        user_config = types.SimpleNamespace(
            core=core,
            get_ext_root_dirs=lambda: [self.ext_dir],
            get_ext_sources=lambda: list(self.sources),
        )
        for target, value in (
            ("user_config", user_config),
            ("PYREVIT_APP_DIR", os.path.join(self.root, "cache")),
        ):
            patcher = patch.object(self.extpackages, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.hosted = {}
        resolve_patch = patch.object(
            self.extpackages.extcatalog, "resolve", side_effect=self._fake_resolve
        )
        resolve_patch.start()
        self.addCleanup(resolve_patch.stop)

    def _write(self, path, *names, **descriptions):
        catalog = json.loads(_catalog_text(*names))
        for entry in catalog["extensions"]:
            entry["description"] = descriptions.get(entry["name"], "from " + path)
        with open(path, "w", encoding="utf-8") as catalog_file:
            json.dump(catalog, catalog_file)
        return path

    def _fake_resolve(self, url, cache_dir, allow_download):
        self.resolved.append(url)
        self.downloads_allowed.append(allow_download)
        return self.hosted.get(url)

    def _packages(self, download_catalogs=True):
        packages = self.extpackages.get_ext_packages(
            authorized_only=False, download_catalogs=download_catalogs
        )
        return {p.name: p for p in packages}

    def test_hosted_catalog_adds_and_overrides_entries(self):
        """New hosted entries appear and hosted info wins over bundled info."""
        self.hosted[DEFAULT_CATALOG_URL] = self._write(
            os.path.join(self.root, "hosted.json"), "Shared", "New", Shared="hosted"
        )
        packages = self._packages()
        self.assertEqual({"Bundled", "Shared", "New"}, set(packages))
        self.assertEqual("hosted", packages["Shared"].description)

    def test_unreachable_hosted_catalog_keeps_bundled(self):
        """No network and no cache: the bundled list still shows."""
        self.assertEqual({"Bundled", "Shared"}, set(self._packages()))
        self.assertEqual([DEFAULT_CATALOG_URL], self.resolved)

    def test_remote_switch_off_skips_every_download(self):
        """extcatalogremote=false keeps the manager fully offline."""
        self.options["extcatalogremote"] = False
        self.sources.append("https://example.com/extra.json")
        self.assertEqual({"Bundled", "Shared"}, set(self._packages()))
        self.assertEqual([], self.resolved)

    def test_configured_url_replaces_default(self):
        """extcatalogurl points the manager at a mirror."""
        self.options["extcatalogurl"] = "https://mirror.example.com/extensions.json"
        self._packages()
        self.assertEqual(["https://mirror.example.com/extensions.json"], self.resolved)

    def test_cli_registered_url_sources_are_downloaded(self):
        """URL sources added with the CLI are no longer silently ignored."""
        extra_url = "https://example.com/extra.json"
        self.sources.append(extra_url)
        self.hosted[extra_url] = self._write(
            os.path.join(self.root, "extra.json"), "Extra"
        )
        self.assertIn("Extra", self._packages())

    def test_local_sources_override_hosted(self):
        """A user's own file source has the last word."""
        self.hosted[DEFAULT_CATALOG_URL] = self._write(
            os.path.join(self.root, "hosted.json"), "Shared", Shared="hosted"
        )
        self.sources.append(
            self._write(os.path.join(self.root, "mine.json"), "Shared", Shared="mine")
        )
        self.assertEqual("mine", self._packages()["Shared"].description)

    def test_later_source_replaces_dependencies(self):
        """Dropping a dependency in the hosted catalog really drops it."""
        bundled = os.path.join(self.ext_dir, "extensions.json")
        with open(bundled, encoding="utf-8") as bundled_file:
            catalog = json.load(bundled_file)
        catalog["extensions"][0]["dependencies"] = ["Shared"]
        with open(bundled, "w", encoding="utf-8") as bundled_file:
            json.dump(catalog, bundled_file)
        hosted = json.loads(_catalog_text("Bundled"))
        hosted["extensions"][0]["dependencies"] = []
        hosted_path = os.path.join(self.root, "hosted.json")
        with open(hosted_path, "w", encoding="utf-8") as hosted_file:
            json.dump(hosted, hosted_file)
        self.hosted[DEFAULT_CATALOG_URL] = hosted_path
        self.assertEqual(set(), self._packages()["Bundled"].dependencies)

    def test_missing_catalog_file_is_skipped(self):
        """A cache file removed between listing and reading does not raise."""
        packages = []
        self.extpackages._update_extpkgs(os.path.join(self.root, "gone.json"), packages)
        self.assertEqual([], packages)

    def test_lookups_never_download(self):
        """Load and command paths read the cache only."""
        self.hosted[DEFAULT_CATALOG_URL] = self._write(
            os.path.join(self.root, "hosted.json"), "New"
        )
        self.assertIsNotNone(self.extpackages.get_ext_package_by_name("New"))
        self.assertEqual([False], self.downloads_allowed)

    def test_manager_listing_allows_download(self):
        """The Extension Manager is the one caller that refreshes catalogs."""
        self._packages(download_catalogs=True)
        self.assertEqual([True], self.downloads_allowed)


if __name__ == "__main__":
    unittest.main()
