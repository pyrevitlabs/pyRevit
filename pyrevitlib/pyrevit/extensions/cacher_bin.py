import pickle

from pyrevit import PyRevitException
import pyrevit.coreutils.appdata as appdata
from pyrevit.coreutils.logger import get_logger


logger = get_logger(__name__)


loaded_extensions = []


def _get_cache_file(cached_ext):
    return appdata.get_data_file(file_id='cache_{}'.format(cached_ext.name),
                                 file_ext='pickle')


def update_cache(parsed_ext):
    try:
        logger.debug('Writing cache for: {}'.format(parsed_ext))
        cache_file = _get_cache_file(parsed_ext)
        logger.debug('Cache file is: {}'.format(cache_file))
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
        logger.debug('Reading cache for: {}'.format(installed_ext))
        cache_file = _get_cache_file(installed_ext)
        logger.debug('Cache file is: {}'.format(cache_file))
        with open(cache_file, 'rb') as bin_cache_file:
            unpickled_pkg = pickle.load(bin_cache_file)
    except Exception as err:
        raise PyRevitException('Error reading cache for: {} | {}'
                               .format(installed_ext, err))

    return unpickled_pkg


def is_cache_valid(extension):
    try:
        cached_ext = get_cached_extension(extension)
        logger.debug('Extension cache directory is: {} for: {}'
                     .format(extension.directory, extension))
        cache_dir_valid = \
            cached_ext.directory == extension.directory

        logger.debug('Extension cache version is: {} for: {}'
                     .format(extension.pyrvt_version, extension))
        cache_version_valid = \
            cached_ext.pyrvt_version == extension.pyrvt_version

        logger.debug('Extension hash value is: {} for: {}'
                     .format(extension.dir_hash_value, extension))
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
        logger.debug('Error reading cache file or file is not available: {}'
                     .format(err))
        return False

    except Exception as err:
        logger.debug('Error determining cache validity: {} | {}'
                     .format(extension, err))
        return False
