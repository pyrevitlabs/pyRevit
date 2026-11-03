"""Download, validate and cache remote extension catalogs.

The Extension Manager reads catalogs from local files. The catalog bundled with
an install is frozen at build time, so entries published afterwards never show
up. This module turns a remote catalog URL (the hosted pyRevit catalog, or an
http(s) source registered with `pyrevit extensions sources add`) into a
validated local copy that the Extension Manager can read like the bundled one.

Important:
    Nothing here raises. A catalog that cannot be downloaded or parsed falls
    back to the last good cached copy, then to nothing, and the caller keeps
    the bundled catalog. The Extension Manager must keep working offline and on
    networks that block GitHub.

Note:
    The catalog is data, never code. Installing an entry still clones the Git
    URL the user picks, and only `https://` catalogs and install URLs are
    accepted.
"""

import hashlib
import json
import os
import os.path as op
import tempfile
import time

from pyrevit.coreutils.logger import get_logger

mlogger = get_logger(__name__)

CACHE_TTL_SECONDS = 24 * 60 * 60
RETRY_AFTER_FAILURE_SECONDS = 10 * 60
DOWNLOAD_TIMEOUT_MS = 5000
CACHE_FILE_PREFIX = "pyRevit_extcatalog_"
CATALOG_LIST_KEY = "extensions"
SECURE_SCHEME = "https://"
TEXT_FIELDS = (
    "type",
    "description",
    "website",
    "image",
    "author",
    "author_profile",
)
FLAG_FIELDS = ("builtin", "default_enabled", "rocket_mode_compatible")
NAME_LIST_FIELDS = ("dependencies", "authusers", "authgroups")

_last_failure_time = {}


class CatalogError(Exception):
    """Raised when a downloaded catalog is not usable."""


def is_remote_source(source):
    """Tell whether an extension source is a URL rather than a local file.

    Args:
        source (str): an entry of the extension sources list.

    Returns:
        (bool): True for http(s) URLs.
    """
    return hasattr(source, "lower") and source.strip().lower().startswith(
        ("http://", SECURE_SCHEME)
    )


def _is_secure_url(value):
    return hasattr(value, "lower") and value.strip().lower().startswith(SECURE_SCHEME)


def _is_text(value):
    return hasattr(value, "strip")


def _is_name_list(value):
    return isinstance(value, list) and all(_is_text(item) for item in value)


def _is_usable_entry(entry):
    """Tell whether `ExtensionPackage.update_info` can consume an entry safely.

    Invariant:
        Every field `update_info` reads must be type-checked here; a wrong type
        that slips through raises while the Extension Manager builds its list,
        outside any fallback.
    """
    if not isinstance(entry, dict):
        return False
    if not (_is_text(entry.get("name")) and entry["name"].strip()):
        return False
    if not _is_secure_url(entry.get("url")):
        return False
    for field in TEXT_FIELDS:
        if field in entry and not _is_text(entry[field]):
            return False
    for field in FLAG_FIELDS:
        if field in entry and not (
            _is_text(entry[field]) or isinstance(entry[field], bool)
        ):
            return False
    for field in NAME_LIST_FIELDS:
        if field in entry and not _is_name_list(entry[field]):
            return False
    return True


def parse_catalog(text):
    """Parse catalog text and drop entries an installed pyRevit must not offer.

    Args:
        text (str): downloaded catalog content.

    Returns:
        (dict): `{"extensions": [...]}` holding only entries with a name, an
            `https://` install URL and correctly typed fields.

    Raises:
        CatalogError: when the text is not a catalog or holds no usable entry,
            so the caller keeps the previous cached copy instead.

    Invariant:
        Must accept everything `dev/scripts/check_extension_catalog.py`
        accepts, so a catalog that passed CI is never rejected here.
    """
    try:
        catalog = json.loads(text)
    except ValueError as parse_err:
        raise CatalogError("not valid JSON: {}".format(parse_err))

    if not isinstance(catalog, dict) or not isinstance(
        catalog.get(CATALOG_LIST_KEY), list
    ):
        raise CatalogError("missing the '{}' list".format(CATALOG_LIST_KEY))

    entries = []
    for entry in catalog[CATALOG_LIST_KEY]:
        if _is_usable_entry(entry):
            entries.append(entry)
        else:
            mlogger.debug("Skipping unusable catalog entry: %s", entry)

    if not entries:
        raise CatalogError("no usable entry")

    return {CATALOG_LIST_KEY: entries}


def cache_file_path(url, cache_dir):
    """Return the cache file a catalog URL is stored in.

    Args:
        url (str): catalog URL.
        cache_dir (str): folder holding cached catalogs.

    Returns:
        (str): stable per-URL path, shared by every Revit version.
    """
    digest = hashlib.sha1(url.strip().encode("utf-8")).hexdigest()[:16]
    return op.join(cache_dir, CACHE_FILE_PREFIX + digest + ".json")


def download_text(url, timeout_ms=DOWNLOAD_TIMEOUT_MS):
    """Download a URL as UTF-8 text with .NET, honouring the system proxy.

    Args:
        url (str): URL to download; redirects are followed.
        timeout_ms (int): connect and read timeout in milliseconds.

    Returns:
        (str): response body.

    Raises:
        Exception: any network or HTTP error from .NET.
    """
    from pyrevit import framework

    request = framework.WebRequest.Create(url)
    request.Timeout = timeout_ms
    request.ReadWriteTimeout = timeout_ms
    response = request.GetResponse()
    try:
        reader = framework.IO.StreamReader(
            response.GetResponseStream(), framework.Encoding.UTF8
        )
        try:
            return reader.ReadToEnd()
        finally:
            reader.Dispose()
    finally:
        response.Close()


def _is_fresh(path, now):
    return op.isfile(path) and 0 <= now - op.getmtime(path) < CACHE_TTL_SECONDS


def _replace_file(source, destination):
    replace = getattr(os, "replace", None)
    if replace:
        replace(source, destination)
        return
    from pyrevit import framework

    if framework.File.Exists(destination):
        framework.File.Replace(source, destination, None)
    else:
        framework.File.Move(source, destination)


def _write_cache(path, catalog):
    """Write the cache so readers always see a whole file.

    Each writer uses its own temporary file, then swaps it in with an atomic
    replace, so concurrent Revit sessions never truncate each other's copy and
    no reader finds the cache missing.
    """
    folder = op.dirname(path)
    if not op.isdir(folder):
        os.makedirs(folder)
    handle, temp_path = tempfile.mkstemp(
        prefix=op.basename(path) + ".", suffix=".tmp", dir=folder
    )
    try:
        os.write(handle, json.dumps(catalog, indent=2).encode("utf-8"))
    finally:
        os.close(handle)
    try:
        _replace_file(temp_path, path)
    except Exception:
        if op.exists(temp_path):
            os.remove(temp_path)
        raise


def resolve(
    url, cache_dir, download=download_text, now=None, force=False, allow_download=True
):
    """Return a local file holding the catalog at `url`, refreshing it if stale.

    A cached copy younger than `CACHE_TTL_SECONDS` is used as is. Otherwise the
    catalog is downloaded, validated with `parse_catalog` and cached. After a
    failed download the URL is not retried for `RETRY_AFTER_FAILURE_SECONDS`,
    so an offline session does not wait on every catalog read.

    Args:
        url (str): catalog URL; only `https://` is fetched.
        cache_dir (str): folder holding cached catalogs.
        download (callable): `download(url, timeout_ms) -> str`.
        now (float): current time in seconds; defaults to `time.time()`.
        force (bool): download even when the cache is fresh or a recent
            attempt failed.
        allow_download (bool): False returns the cached copy whatever its age
            and never touches the network.

    Returns:
        (str | None): path of the cached catalog, possibly stale when the
            download failed, or None when there is no usable copy.

    Side Effects:
        Network call, and writes the cache file under `cache_dir`.
    """
    if not _is_secure_url(url):
        mlogger.warning("Ignoring extension catalog that is not https: %s", url)
        return None

    if now is None:
        now = time.time()
    cache_path = cache_file_path(url, cache_dir)
    cached = cache_path if op.isfile(cache_path) else None

    if not allow_download:
        return cached

    if not force:
        if _is_fresh(cache_path, now):
            return cache_path
        last_failure = _last_failure_time.get(url)
        if (
            last_failure is not None
            and now - last_failure < RETRY_AFTER_FAILURE_SECONDS
        ):
            return cached

    try:
        catalog = parse_catalog(download(url, DOWNLOAD_TIMEOUT_MS))
        _write_cache(cache_path, catalog)
    except Exception as fetch_err:
        _last_failure_time[url] = now
        mlogger.warning(
            "Can not refresh extension catalog %s, using %s | %s",
            url,
            "cached copy" if cached else "bundled catalog only",
            fetch_err,
        )
        return cached

    _last_failure_time.pop(url, None)
    return cache_path
