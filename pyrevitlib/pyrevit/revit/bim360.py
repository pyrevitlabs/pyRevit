"""BIM360-related utilities."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import os
import os.path as op

from pyrevit import HOST_APP
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit.revit import files

mlogger = get_logger(__name__)


COLLAB_CACHE_PATH_FORMAT = \
    '%LOCALAPPDATA%/Autodesk/Revit/Autodesk Revit {version}/CollaborationCache'


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


def get_collab_caches():
    """Get a list of project caches stored under collaboration cache."""
    collab_root = op.normpath(op.expandvars(
        COLLAB_CACHE_PATH_FORMAT.format(version=HOST_APP.version)
    ))
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
