"""Utility functions for managing pyRevit versions.

Examples:
        ```python
        from pyrevit import versionmgr
        v = versionmgr.get_pyrevit_version()
        v.get_formatted()
        ```
        '4.10-beta2'
"""

import os.path as op
import re

from pyrevit import HOME_DIR, BIN_DIR
from pyrevit import VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH, BUILD_METADATA
from pyrevit import PYREVIT_CLI_PATH
from pyrevit.compat import safe_strtype
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import envvars
from pyrevit.coreutils import git


# pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)

VERSION_REGEX = r"\A(\d+)\.(\d+)\.(\d+)\.?(.+)?\Z"


def parse_version_string(version_string):
    """Split a version string into (major, minor, patch, metadata) parts.

    The whole value has to be a version. An unanchored match would let a malformed
    session value contribute a version to the string the About window shows, which
    is the same class of stale report this module exists to prevent.

    Args:
        version_string (str): version string, e.g. "7.0.0.26273+1554"

    Returns:
        (tuple): (int, int, int, str) parts, or None if the string is not a version
    """
    if not version_string:
        return None

    try:
        matches = re.findall(VERSION_REGEX, safe_strtype(version_string).strip())[0]
    except (IndexError, re.error):
        return None

    try:
        major, minor, patch = (int(matches[0]), int(matches[1]), int(matches[2]))
    except (TypeError, ValueError):
        return None

    metadata = matches[3] if len(matches) == 4 else ""
    return major, minor, patch, metadata


def get_loaded_build_version():
    """Version of the build the running session loaded, or None.

    The loader seeds ``PYREVIT_VERSION`` from the informational version of the loaded
    pyRevit Runtime assembly, so this is the build actually executing in Revit. The
    version file in the clone describes the checkout instead, and the two disagree
    whenever the clone's ``bin/`` came from a release image or from CI artifacts.

    Returns:
        (str): version string of the loaded build, or None outside a session
    """
    try:
        return envvars.get_pyrevit_env_var(envvars.VERSION_ENVVAR)
    except Exception as env_err:
        mlogger.debug("Can not read the session build version. | %s", env_err)
    return None


class _PyRevitVersion(object):
    """pyRevit version wrapper.

    Args:
        commit_hash (str): signature
        build_version (str): version of the loaded build, or None to fall back on
            the version file in the clone
    """

    major = VERSION_MAJOR
    minor = VERSION_MINOR
    patch = VERSION_PATCH
    metadata = BUILD_METADATA
    signature = ""

    def __init__(self, signature, build_version=None):
        self.signature = safe_strtype(signature)[:7]

        parsed = parse_version_string(build_version)
        if parsed:
            self.major, self.minor, self.patch, self.metadata = parsed
        else:
            self.major = _PyRevitVersion.major
            self.minor = _PyRevitVersion.minor
            self.patch = _PyRevitVersion.patch
            self.metadata = _PyRevitVersion.metadata

    def as_int_tuple(self):
        """Returns version as an int tuple (major, minor, patch).

        Every source of `patch` is already an int: `pyrevit.VERSION_PATCH` is
        parsed with `int()` and so is `parse_version_string`. Reinterpreting it
        with a base would turn a two-digit decimal patch into a different
        number.
        """
        return (self.major, self.minor, self.patch)

    def as_str_tuple(self):
        """Returns version as an string tuple ('major', 'minor', 'patch')."""
        ver_tuple = (
            safe_strtype(self.major),
            safe_strtype(self.minor),
            safe_strtype(self.patch),
        )
        return ver_tuple

    def get_formatted(self, strict=False, extended=False):
        """Returns 'major.minor.patch' in string."""
        formatted_ver = "{}.{}.{}".format(self.major, self.minor, self.patch)

        if not strict and self.metadata:
            formatted_ver += "." + self.metadata

        if extended and not strict:
            formatted_ver += ":" + self.signature

        return formatted_ver


def get_pyrevit_repo():
    """Return pyRevit repository.

    Returns:
        (pyrevit.coreutils.git.RepoInfo): repo wrapper object
    """
    try:
        return git.get_repo(HOME_DIR)
    except Exception as repo_err:
        mlogger.debug("Can not create repo from directory: %s | %s", HOME_DIR, repo_err)


def get_pyrevit_version():
    """Return information about active pyRevit version.

    The version reported is the one stamped into the assemblies the session loaded,
    falling back on the clone's version file when no session is running.

    Returns:
        (_PyRevitVersion): version wrapper object
    """
    try:
        commit_hash = get_pyrevit_repo().last_commit_hash
    except Exception as ver_err:
        mlogger.debug("Can not get pyRevit patch number. | %s", ver_err)
        commit_hash = ""

    return _PyRevitVersion(commit_hash, get_loaded_build_version())


def get_pyrevit_cli_version():
    """Return version of shipped pyRevit CLI utility.

    Returns:
        (str): version string of pyRevit CLI utility binary
    """
    return coreutils.get_exe_version(PYREVIT_CLI_PATH)
