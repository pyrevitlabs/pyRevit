"""BIM360-related utilities. Other names by Autodesk: ACC, Forma"""
import os
import os.path as op

from pyrevit import HOST_APP
from pyrevit import coreutils
from pyrevit.compat import configparser
from pyrevit.coreutils.logger import get_logger
from pyrevit.revit import files

mlogger = get_logger(__name__)


COLLAB_CACHE_PATH_FORMAT = \
    '%LOCALAPPDATA%/Autodesk/Revit/Autodesk Revit {version}/CollaborationCache'

REVIT_INI_PATH_FORMAT = \
    '%APPDATA%/Autodesk/Revit/Autodesk Revit {version}/Revit.ini'

CLOUD_MODEL_CACHE_SECTION = 'CloudModelCache'
CLOUD_MODEL_CACHE_KEY = 'CacheLocation'

# Revit 2024 is the first version to support custom cloud cache paths
CUSTOM_CACHE_MIN_VERSION = 2024


class CollabCacheModel(object):
    """Collaboration cache for a Revit project."""
    def __init__(self, model_path):
        self.model_path = model_path
        self.model_dir = op.dirname(model_path)
        self.model_name_ex = op.basename(model_path)
        self.model_name = op.splitext(self.model_name_ex)[0]

        self.central_cache_model_path = \
            op.join(self.model_dir, 'CentralCache', self.model_name_ex)
        self.model_backup_path = \
            op.join(self.model_dir, '{}_backup'.format(self.model_name))

        try:
            finfo = files.get_file_info(self.model_path)
            self.product = finfo.RevitProduct.Name
            self.project = op.basename(finfo.CentralModelPath)
        except Exception:
            self.product = "?"
            self.project = self.model_name_ex

    def __str__(self):
        return '<{} id={} revit={}>'.format(
            self.__class__.__name__,
            self.model_name_ex,
            self.product
            )


class CollabCache(object):
    """Collaboration cache instance containing multiple projects."""
    def __init__(self, cache_path):
        self.cache_path = cache_path
        self.cache_id = op.basename(cache_path)
        self.cache_models = []
        for entry in os.listdir(self.cache_path):
            if entry.lower().endswith('.rvt'):
                self.cache_models.append(
                    CollabCacheModel(op.join(cache_path, entry))
                    )

        self.cache_linked_models = []
        lmodels_path = op.join(self.cache_path, 'LinkedModels')
        if op.exists(lmodels_path):
            for entry in os.listdir(lmodels_path):
                if entry.lower().endswith('.rvt'):
                    self.cache_linked_models.append(
                        CollabCacheModel(op.join(lmodels_path, entry))
                        )

    def __str__(self):
        return '<{} id={}>'.format(self.__class__.__name__, self.cache_id)


def _get_custom_cache_root(version):
    """Read CacheLocation from Revit.ini for Revit 2024+.

    Returns the expanded, normalised path if a valid non-empty value is found,
    otherwise returns None so the caller falls back to the default location.

    Args:
        version (str): Revit version string, e.g. '2024'.
    """
    try:
        version_int = int(version)
    except (ValueError, TypeError):
        return None

    if version_int < CUSTOM_CACHE_MIN_VERSION:
        return None

    ini_path = op.normpath(op.expandvars(
        REVIT_INI_PATH_FORMAT.format(version=version)
    ))
    mlogger.debug('checking Revit.ini for custom cache path: %s', ini_path)

    if not op.isfile(ini_path):
        mlogger.debug('Revit.ini not found: %s', ini_path)
        return None

    try:
        cfg = configparser.ConfigParser()
        cfg.read(ini_path)
    except Exception as ini_ex:
        mlogger.warning('Failed to read Revit.ini @ %s | %s', ini_path, str(ini_ex))
        return None

    if not cfg.has_section(CLOUD_MODEL_CACHE_SECTION):
        mlogger.debug('No [%s] section in Revit.ini', CLOUD_MODEL_CACHE_SECTION)
        return None

    if not cfg.has_option(CLOUD_MODEL_CACHE_SECTION, CLOUD_MODEL_CACHE_KEY):
        mlogger.debug('No %s key in [%s]', CLOUD_MODEL_CACHE_KEY, CLOUD_MODEL_CACHE_SECTION)
        return None

    raw = cfg.get(CLOUD_MODEL_CACHE_SECTION, CLOUD_MODEL_CACHE_KEY, raw=True).strip()
    if not raw:
        mlogger.debug('Empty CacheLocation in Revit.ini')
        return None

    custom_path = op.normpath(op.expandvars(raw))
    mlogger.debug('custom cache root from Revit.ini: %s', custom_path)
    return custom_path


def _get_collab_cache_root(version):
    """Resolve the collaboration cache root for the given Revit version.

    For Revit 2024+ checks Revit.ini for a custom CacheLocation first,
    falling back to the default %LOCALAPPDATA% path for all versions.

    Args:
        version (str): Revit version string, e.g. '2024'.

    Returns:
        str: Normalised absolute path to the collaboration cache root.
    """
    custom = _get_custom_cache_root(version)
    if custom and op.isdir(custom):
        return custom

    default = op.normpath(op.expandvars(
        COLLAB_CACHE_PATH_FORMAT.format(version=version)
    ))
    mlogger.debug('using default cache root: %s', default)
    return default


def get_collab_caches():
    """Get a list of project caches stored under collaboration cache."""
    collab_root = _get_collab_cache_root(HOST_APP.version)
    mlogger.debug('cache root: %s', collab_root)
    collab_caches = []
    if op.exists(collab_root):
        for cache_root in os.listdir(collab_root):
            cache_root_path = op.join(collab_root, cache_root)
            for cache_inst in os.listdir(cache_root_path):
                cache_inst_path = op.join(cache_root_path, cache_inst)
                mlogger.debug('cache inst: %s', cache_inst_path)
                if op.isdir(cache_inst_path):
                    collab_caches.append(
                        CollabCache(cache_inst_path)
                        )
    return collab_caches


def clear_model_cache(collab_cache_model):
    """Clear caches for given collaboration cache model.

    Args:
        collab_cache_model (bim360.CollabCacheModel): cache model to clear
    """
    if isinstance(collab_cache_model, CollabCacheModel):
        cm = collab_cache_model
        mlogger.debug('Deleting %s', cm.model_path)
        try:
            if op.exists(cm.model_path):
                os.remove(cm.model_path)
        except Exception as cmdel_ex:
            mlogger.error(
                'Error deleting model cache @ %s | %s',
                cm.model_path,
                str(cmdel_ex)
                )

        mlogger.debug('Deleting %s', cm.model_backup_path)
        try:
            if op.exists(cm.model_backup_path):
                coreutils.fully_remove_dir(cm.model_backup_path)
        except Exception as cmbdel_ex:
            mlogger.error(
                'Error deleting model backup @ %s | %s',
                cm.model_backup_path,
                str(cmbdel_ex)
                )

        mlogger.debug('Deleting %s', cm.central_cache_model_path)
        try:
            if op.exists(cm.central_cache_model_path):
                os.remove(cm.central_cache_model_path)
        except Exception as ccmdel_ex:
            mlogger.error(
                'Error deleting central model cache @ %s | %s',
                cm.central_cache_model_path,
                str(ccmdel_ex)
                )
