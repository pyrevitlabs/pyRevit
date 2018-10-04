"""Base module to handle extension binary caching."""
import pickle

from pyrevit import PyRevitException
from pyrevit.coreutils import appdata
from pyrevit.coreutils.logger import get_logger

#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


loaded_extensions = []


def _get_cache_file(cached_ext):
    return appdata.get_data_file(file_id='cache_{}'.format(cached_ext.name),
                                 file_ext='pickle')


def update_cache(parsed_ext):
    try:
        mlogger.debug('Writing cache for: %s', parsed_ext)
        cache_file = _get_cache_file(parsed_ext)
        mlogger.debug('Cache file is: %s', cache_file)
        with open(cache_file, 'wb') as bin_cache_file:
            pickle.dump(parsed_ext, bin_cache_file, pickle.HIGHEST_PROTOCOL)
    except Exception as err:
        raise PyRevitException('Error writing cache for: {} | {}'
                               .format(parsed_ext, err))


def get_cached_extension(installed_ext):
    for loaded_ext in loaded_extensions:
        if loaded_ext.name == installed_ext.name:
            return loaded_ext

    try:
        mlogger.debug('Reading cache for: %s', installed_ext)
        cache_file = _get_cache_file(installed_ext)
        mlogger.debug('Cache file is: %s', cache_file)
        with open(cache_file, 'rb') as bin_cache_file:
            unpickled_pkg = pickle.load(bin_cache_file)
    except Exception as err:
        raise PyRevitException('Error reading cache for: {} | {}'
                               .format(installed_ext, err))

    return unpickled_pkg


def is_cache_valid(extension):
    try:
        cached_ext = get_cached_extension(extension)
        mlogger.debug('Extension cache directory is: %s for: %s',
                      extension.directory, extension)
        cache_dir_valid = \
            cached_ext.directory == extension.directory

        mlogger.debug('Extension cache version is: %s for: %s',
                      extension.pyrvt_version, extension)
        cache_version_valid = \
            cached_ext.pyrvt_version == extension.pyrvt_version

        mlogger.debug('Extension hash value is: %s for: %s',
                      extension.dir_hash_value, extension)
        cache_hash_valid = \
            cached_ext.dir_hash_value == extension.dir_hash_value

        cache_valid = \
            cache_dir_valid and cache_version_valid and cache_hash_valid

        # add loaded package to list so it can be recovered later
        if cache_valid:
            loaded_extensions.append(cached_ext)

        # cache is valid if both version and hash value match
        return cache_valid

    except PyRevitException as err:
        mlogger.debug('Error reading cache file or file is not available: %s',
                      err)
        return False

    except Exception as err:
        mlogger.debug('Error determining cache validity: %s | %s',
                      extension, err)
        return False
