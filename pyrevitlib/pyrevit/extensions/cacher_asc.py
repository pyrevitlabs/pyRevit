import json

from pyrevit import PyRevitException
import pyrevit.coreutils.appdata as appdata
from pyrevit.coreutils import get_all_subclasses
from pyrevit.coreutils.logger import get_logger


logger = get_logger(__name__)


EXT_HASH_VALUE_KEY = 'dir_hash_value'
EXT_HASH_VERSION_KEY = 'pyrvt_version'
EXT_DIR_KEY = 'directory'
SUB_CMP_KEY = '_sub_components'
TYPE_ID_KEY = 'type_id'
NAME_KEY = 'name'


def _get_cache_file(cached_ext):
    return appdata.get_data_file(file_id='cache_{}'.format(cached_ext.name),
                                 file_ext='json')


def _make_cache_from_cmp(obj):
    return json.dumps(obj,
                      default=lambda o: o.get_cache_data(),
                      sort_keys=True,
                      indent=4)


def _make_sub_cmp_from_cache(parent_cmp, cached_sub_cmps):
    logger.debug('Processing cache for: %s', parent_cmp)
    # get allowed classes under this component
    allowed_sub_cmps = get_all_subclasses(parent_cmp.allowed_sub_cmps)
    logger.debug('Allowed sub components are: %s', allowed_sub_cmps)
    # iterate through list of cached sub components
    for cached_cmp in cached_sub_cmps:  # type: dict
        for sub_class in allowed_sub_cmps:
            if sub_class.type_id == cached_cmp[TYPE_ID_KEY]:
                logger.debug('Creating sub component from cache: {}, {}'
                             .format(cached_cmp[NAME_KEY], sub_class))

                # cached_cmp might contain SUB_CMP_KEY. This needs to be
                # removed since this function will make all the children
                # recursively. So if this component has SUB_CMP_KEY means
                # it has sub components:
                sub_cmp_cache = None
                if SUB_CMP_KEY in cached_cmp.keys():
                    # drop subcomponents dict from cached_cmp since we
                    # don't want the loaded_cmp to include this
                    sub_cmp_cache = cached_cmp.pop(SUB_CMP_KEY)

                # create sub component from cleaned cached_cmp
                loaded_cmp = sub_class()
                loaded_cmp.load_cache_data(cached_cmp)

                # now process sub components for loaded_cmp if any
                if sub_cmp_cache:
                    _make_sub_cmp_from_cache(loaded_cmp, sub_cmp_cache)

                parent_cmp.add_component(loaded_cmp)


def _read_cache_for(cached_ext):
    try:
        logger.debug('Reading cache for: %s', cached_ext)
        cache_file = _get_cache_file(cached_ext)
        logger.debug('Cache file is: %s', cache_file)
        with open(_get_cache_file(cached_ext), 'r') as cache_file:
            cached_tab_dict = json.load(cache_file)
        return cached_tab_dict
    except Exception as err:
        raise PyRevitException('Error reading cache for: {} | {}'
                               .format(cached_ext, err))


def _write_cache_for(parsed_ext):
    try:
        logger.debug('Writing cache for: %s', parsed_ext)
        cache_file = _get_cache_file(parsed_ext)
        logger.debug('Cache file is: %s', cache_file)
        with open(cache_file, 'w') as cache_file:
            cache_file.write(_make_cache_from_cmp(parsed_ext))
    except Exception as err:
        raise PyRevitException('Error writing cache for: {} | {}'
                               .format(parsed_ext, err))


def update_cache(parsed_ext):
    logger.debug('Updating cache for tab: %s ...', parsed_ext.name)
    _write_cache_for(parsed_ext)
    logger.debug('Cache updated for tab: %s', parsed_ext.name)


def get_cached_extension(installed_ext):
    cached_ext_dict = _read_cache_for(installed_ext)
    try:
        logger.debug('Constructing components from cache for: {}'
                     .format(installed_ext))
        # get cached sub component dictionary and call recursive maker function
        _make_sub_cmp_from_cache(installed_ext,
                                 cached_ext_dict.pop(SUB_CMP_KEY))
        logger.debug('Load successful...')
    except Exception as err:
        logger.debug('Error reading cache...')
        raise PyRevitException(err)

    return installed_ext


def is_cache_valid(extension):
    try:
        cached_ext_dict = _read_cache_for(extension)  # type: dict
        logger.debug('Extension cache directory is: {} for: {}'
                     .format(extension.directory, extension))
        cache_dir_valid = cached_ext_dict[EXT_DIR_KEY] == extension.directory

        logger.debug('Extension cache version is: {} for: {}'
                     .format(extension.pyrvt_version, extension))
        cache_version_valid = \
            cached_ext_dict[EXT_HASH_VERSION_KEY] == extension.pyrvt_version

        logger.debug('Extension hash value is: {} for: {}'
                     .format(extension.dir_hash_value, extension))
        cache_hash_valid = \
            cached_ext_dict[EXT_HASH_VALUE_KEY] == extension.dir_hash_value

        cache_valid = \
            cache_dir_valid and cache_version_valid and cache_hash_valid

        # cache is valid if both version and hash value match
        return cache_valid

    except PyRevitException as err:
        logger.debug(err)
        return False

    except Exception as err:
        logger.debug('Error determining cache validity: {} | {}'
                     .format(extension, err))
