"""Perform upgrades between version, e.g. adding a new config parameter."""
#pylint: disable=W0611
import os
import os.path as op
import shutil
import time

from pyrevit.coreutils import appdata
from pyrevit.coreutils.logger import get_logger


mlogger = get_logger(__name__)

TELEMETRY_FIELD_MAX_LEN = 8192
TELEMETRY_BLOAT_FIELDS = (
    'telemetry_file_dir',
    'telemetry_server_url',
    'apptelemetry_server_url',
)


def heal_bloated_telemetry_fields(user_config):
    """Detect and reset telemetry config fields corrupted by escape-doubling.
    Args:
        user_config (:obj:`pyrevit.userconfig.PyRevitConfig`): config object

    Returns:
        list[str]: names of fields that were reset, empty list if none.
    """
    if not user_config.has_section('telemetry'):
        return []

    section = user_config.telemetry
    bloated = []
    for field_name in TELEMETRY_BLOAT_FIELDS:
        if not section.has_option(field_name):
            continue
        try:
            raw_value = section._parser.get(section._section_name,  #pylint: disable=W0212
                                            field_name)
        except Exception as read_err:
            mlogger.debug(
                'Could not read telemetry field %r for bloat check | %s',
                field_name, read_err)
            continue
        if len(raw_value) > TELEMETRY_FIELD_MAX_LEN:
            bloated.append((field_name, len(raw_value)))

    if not bloated:
        return []
    # Take a backup before mutating the in-memory parser. If we cannot
    # produce a backup of the on-disk file, abort the heal so the user
    # still has a recoverable copy of whatever was previously stored.
    # The next reload will retry the heal once the issue (disk full,
    # ACLs, etc.) is resolved.
    cfg_path = user_config.config_file
    if cfg_path and op.exists(cfg_path):
        timestamp = time.strftime('%Y%m%d-%H%M%S')
        backup_path = '{}.bloated.{}.bak'.format(cfg_path, timestamp)
        try:
            shutil.copy2(cfg_path, backup_path)
            mlogger.info('Backed up bloated config to: %s', backup_path)
        except Exception as backup_err:
            mlogger.error(
                'Could not back up bloated config to %s | %s. '
                'Skipping heal to preserve recoverable copy on disk.',
                backup_path, backup_err)
            return []

    healed = []
    for field_name, original_len in bloated:
        try:
            setattr(section, field_name, '')
            healed.append(field_name)
            mlogger.warning(
                'Reset bloated telemetry config field %r '
                '(was %d chars, known escape-doubling bug). '
                'If telemetry was previously configured, reconfigure '
                'via Settings > Telemetry.',
                field_name, original_len)
        except Exception as set_err:
            mlogger.error(
                'Detected bloated telemetry field %r (%d chars) '
                'but could not reset it | %s',
                field_name, original_len, set_err)

    return healed


def upgrade_user_config(user_config):   #pylint: disable=W0613
    """Upgarde user configurations.

    Args:
        user_config (:obj:`pyrevit.userconfig.PyRevitConfig`): config object
    """
    # Heal known config corruption before any other upgrade work runs.
    heal_bloated_telemetry_fields(user_config)

    # upgrade value formats
    for section in user_config:
        for option in section:
            setattr(section, option, getattr(section, option))


def remove_leftover_temp_files():
    """4.8.5 had a bug that would create temp files with extension ..bak.

    This cleans them up.
    """
    univ_path = op.dirname(appdata.get_universal_data_file("X", 'bak'))
    if op.exists(univ_path):
        for entry in os.listdir(univ_path):
            if op.isfile(entry) and entry.lower().endswith('..bak'):
                appdata.garbage_data_file(op.join(univ_path, entry))


def upgrade_existing_pyrevit():
    """Upgrade existing pyRevit deployment."""
    remove_leftover_temp_files()
