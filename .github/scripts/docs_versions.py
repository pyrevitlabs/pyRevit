"""Maintain the versioned layout of the docs on the gh-pages branch.

Called by publish-gh-pages.sh after it has copied a built site into
``<pages-dir>/<version>/``. Records the version in ``versions.json`` (the
format Material for MkDocs reads with ``extra.version.provider: mike``),
then rebuilds everything at the root that is derived from the latest
release:

- ``latest/``: a copy of the highest ``X.Y`` version.
- A redirect page for every page of ``latest/``, so links to the old
  unversioned site (``/get-started/``) and the root ``index.html`` still
  resolve.
- ``404.html``, ``robots.txt`` and ``llms.txt``.

Invariant:
    Root entries other than ``.git``, ``pr-preview/``, ``CNAME``,
    ``versions.json`` and the version folders are regenerated on every run,
    so anything else placed at the root is deleted. While no ``X.Y`` version
    exists, the root is left untouched, so deploying ``dev`` first does not
    take down the legacy unversioned site.
"""

import json
import re
import shutil
import sys
from pathlib import Path

LATEST = "latest"
DEV = "dev"
PREVIEW_ROOT = "pr-preview"
KEPT_ROOT_FILES = {".git", PREVIEW_ROOT, "CNAME", "versions.json", ".nojekyll"}
VERSION_PATTERN = re.compile(r"^(dev|\d+\.\d+)$")
REDIRECT_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Redirecting</title>
{canonical}<meta http-equiv="refresh" content="0; url={target}">
<script>location.replace("{target}" + location.search + location.hash);</script>
</head>
<body><a href="{target}">Redirecting to {target}</a></body>
</html>
"""
NOT_FOUND_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Page not found - pyRevit</title>
</head>
<body>
<h1>Page not found</h1>
<p>Go to the <a href="/{latest}/">latest pyRevit documentation</a>.</p>
</body>
</html>
"""


def version_key(version):
    """Sort key: ``dev`` first, then releases from newest to oldest."""
    if version == DEV:
        return (0, ())
    return (1, tuple(-int(part) for part in version.split(".")))


def update_versions(pages_dir, version):
    """Add ``version`` to versions.json.

    Returns:
        tuple: The latest release (None when there is none) and the set of
        all published versions.
    """
    versions_file = pages_dir / "versions.json"
    versions = set()
    if versions_file.exists():
        versions = {
            entry["version"]
            for entry in json.loads(versions_file.read_text(encoding="utf-8"))
            if (pages_dir / entry["version"]).is_dir()
        }
    versions.add(version)
    releases = [v for v in versions if v != DEV]
    latest = min(releases, key=version_key) if releases else None
    entries = [
        {
            "version": v,
            "title": v,
            "aliases": [LATEST] if v == latest else [],
        }
        for v in sorted(versions, key=version_key)
    ]
    versions_file.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    return latest, versions


def remove_derived_root_files(pages_dir, versions):
    """Delete root entries that are not version folders or preserved files."""
    kept = KEPT_ROOT_FILES | versions
    for entry in pages_dir.iterdir():
        if entry.name in kept:
            continue
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()


def write_redirects(pages_dir, reserved, domain):
    """Write a root redirect page for every HTML page of latest/."""
    latest_dir = pages_dir / LATEST
    for page in latest_dir.rglob("*.html"):
        relative = page.relative_to(latest_dir)
        if relative.as_posix() == "404.html" or relative.parts[0] in reserved:
            continue
        stub = pages_dir / relative
        target_path = relative.as_posix()
        if relative.name == "index.html":
            target_path = target_path[: -len("index.html")]
        depth = len(relative.parts) - 1
        target = "../" * depth + f"{LATEST}/{target_path}"
        canonical = ""
        if domain:
            canonical = f'<link rel="canonical" href="https://{domain}/{LATEST}/{target_path}">\n'
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text(
            REDIRECT_PAGE.format(target=target, canonical=canonical),
            encoding="utf-8",
        )


def write_root_files(pages_dir, domain):
    """Write 404.html, robots.txt and llms.txt for the latest release."""
    (pages_dir / "404.html").write_text(
        NOT_FOUND_PAGE.format(latest=LATEST), encoding="utf-8"
    )
    robots = [
        "User-agent: *",
        f"Disallow: /{PREVIEW_ROOT}/",
        f"Disallow: /{DEV}/",
    ]
    if domain:
        robots.append(f"Sitemap: https://{domain}/{LATEST}/sitemap.xml")
    (pages_dir / "robots.txt").write_text("\n".join(robots) + "\n", encoding="utf-8")
    llms = pages_dir / LATEST / "llms.txt"
    if llms.exists():
        text = llms.read_text(encoding="utf-8")
        if domain:
            text = re.sub(
                rf"https://{re.escape(domain)}/(?!{LATEST}/)",
                f"https://{domain}/{LATEST}/",
                text,
            )
        (pages_dir / "llms.txt").write_text(text, encoding="utf-8")
    (pages_dir / ".nojekyll").touch()


def read_domain(pages_dir):
    """Return the custom domain from CNAME, or None."""
    cname = pages_dir / "CNAME"
    if cname.exists():
        return cname.read_text(encoding="utf-8").strip() or None
    return None


def main(argv):
    """Entry point: ``docs_versions.py <pages-dir> <version>``."""
    if len(argv) != 3 or not VERSION_PATTERN.match(argv[2]):
        print(
            "usage: docs_versions.py <pages-dir> <dev|X.Y>",
            file=sys.stderr,
        )
        return 2
    pages_dir = Path(argv[1]).resolve()
    version = argv[2]
    if not (pages_dir / version / "index.html").is_file():
        print(f"error: {pages_dir / version}/index.html not found", file=sys.stderr)
        return 1
    latest, versions = update_versions(pages_dir, version)
    if latest is None:
        print("No release version published yet, leaving the root untouched.")
        return 0
    remove_derived_root_files(pages_dir, versions)
    shutil.copytree(pages_dir / latest, pages_dir / LATEST, symlinks=True)
    domain = read_domain(pages_dir)
    write_redirects(pages_dir, KEPT_ROOT_FILES | versions | {LATEST}, domain)
    write_root_files(pages_dir, domain)
    print(f"Published {version}; {LATEST} is {latest}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
