"""Perform a ONE TIME version-to-version deployment cleanup at session load for 4.8.5."""

import os
import os.path as op

from pyrevit.coreutils import appdata
from pyrevit.coreutils.logger import get_logger

mlogger = get_logger(__name__)


def remove_leftover_temp_files():
    """4.8.5 had a bug that would create temp files with extension ..bak.

    This cleans them up.
    """
    univ_path = op.dirname(appdata.get_universal_data_file("X", "bak"))
    if op.exists(univ_path):
        for entry in os.listdir(univ_path):
            if op.isfile(entry) and entry.lower().endswith("..bak"):
                appdata.garbage_data_file(op.join(univ_path, entry))


def encrypt_plaintext_extension_credentials():
    """Seal any extension credential still stored in plaintext in the config.

    Runs here, once per session, rather than in the session manager: this module is
    where pyRevit keeps one-time deployment migrations, and by the time it runs
    the config is built and any pending upgrade has been applied.

    A failure is logged and swallowed. A config that cannot be migrated is a
    config that still works, and refusing to start Revit over it would be a worse
    outcome than leaving a token where it is.
    """
    try:
        from pyrevit.coreutils import credentials

        credentials.migrate_legacy_credentials()
    except Exception as migration_err:
        mlogger.warning(
            "Could not encrypt the plaintext extension credentials: %s", migration_err
        )


def upgrade_existing_pyrevit():
    """Upgrade existing pyRevit deployment."""
    remove_leftover_temp_files()
    encrypt_plaintext_extension_credentials()
