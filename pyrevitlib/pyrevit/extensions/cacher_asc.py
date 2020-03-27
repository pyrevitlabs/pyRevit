"""Base module to handle extension ASCII caching."""
import json
import codecs

from pyrevit import PyRevitException
from pyrevit.coreutils import appdata
from pyrevit.coreutils import get_all_subclasses
from pyrevit.coreutils.logger import get_logger
from pyrevit.extensions import components as comps
from pyrevit.extensions import genericcomps as gencomps

#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


def _get_cache_file(cached_ext):
    return appdata.get_data_file(file_id='cache_{}'.format(cached_ext.name),
                                 file_ext='json')


def _make_cache_from_cmp(obj):
    return json.dumps(obj,
                      default=lambda o: o.get_cache_data(),
                      sort_keys=True,
                      indent=4,
                      ensure_ascii=False)


def _make_layoutitems_from_cache(parent_cmp, cached_layoutitems):
    if hasattr(parent_cmp, gencomps.LAYOUT_ITEM_KEY):
        litems = []
        for litem_cache in cached_layoutitems:
            # grab the layout directive cache and create component
            ldir = None
            ldir_cache = litem_cache.get(gencomps.LAYOUT_DIR_KEY, {})
            if ldir_cache:
                ldir = gencomps.LayoutDirective()
                ldir.load_cache_data(ldir_cache)

            litem = gencomps.LayoutItem()
            litem.load_cache_data(litem_cache)
            # set the layout directive
            setattr(litem, gencomps.LAYOUT_DIR_KEY, ldir)
            litems.append(litem)
        setattr(parent_cmp, gencomps.LAYOUT_ITEM_KEY, litems)


def _make_sub_cmp_from_cache(parent_cmp, cached_sub_cmps):
    mlogger.debug('Processing cache for: %s', parent_cmp)
    # get allowed classes under this component
    allowed_sub_cmps = get_all_subclasses(parent_cmp.allowed_sub_cmps)
    mlogger.debug('Allowed sub components are: %s', allowed_sub_cmps)
    # iterate through list of cached sub components
    for cached_cmp in cached_sub_cmps:  # type: dict
        for sub_class in allowed_sub_cmps:
            if sub_class.type_id == cached_cmp[gencomps.TYPE_ID_KEY]:
                mlogger.debug('Creating sub component from cache: %s, %s',
                              cached_cmp[gencomps.NAME_KEY], sub_class)

                # cached_cmp might contain gencomps.SUB_CMP_KEY. This needs to be
                # removed since this function will make all the children
                # recursively. So if this component has gencomps.SUB_CMP_KEY means
                # it has sub components:
                sub_cmp_cache = None
                if gencomps.SUB_CMP_KEY in cached_cmp.keys():
                    # drop subcomponents dict from cached_cmp since we
                    # don't want the loaded_cmp to include this
                    sub_cmp_cache = cached_cmp.pop(gencomps.SUB_CMP_KEY)

                # grab the layout items
                # layoutitems_cache is list[dict]
                layoutitems_cache = None
                if gencomps.LAYOUT_ITEM_KEY in cached_cmp.keys():
                    # drop layoutitems dict from cached_cmp since we
                    # don't want the loaded_cmp to include this
                    layoutitems_cache = cached_cmp.pop(gencomps.LAYOUT_ITEM_KEY)

                # create sub component from cleaned cached_cmp
                loaded_cmp = sub_class()
                loaded_cmp.load_cache_data(cached_cmp)

                # now process sub components for loaded_cmp if any
                if sub_cmp_cache:
                    _make_sub_cmp_from_cache(loaded_cmp, sub_cmp_cache)

                # apply layout items
                if layoutitems_cache:
                    _make_layoutitems_from_cache(loaded_cmp, layoutitems_cache)

                parent_cmp.add_component(loaded_cmp)


def _read_cache_for(cached_ext):
    try:
        mlogger.debug('Reading cache for: %s', cached_ext)
        cache_file = _get_cache_file(cached_ext)
        mlogger.debug('Cache file is: %s', cache_file)
        with codecs.open(_get_cache_file(cached_ext), 'r', 'utf-8') \
                as cache_file:
            cached_tab_dict = json.load(cache_file)
        return cached_tab_dict
    except Exception as err:
        raise PyRevitException('Error reading cache for: {} | {}'
                               .format(cached_ext, err))


def _write_cache_for(parsed_ext):
    try:
        mlogger.debug('Writing cache for: %s', parsed_ext)
        cache_file = _get_cache_file(parsed_ext)
        mlogger.debug('Cache file is: %s', cache_file)
        with codecs.open(cache_file, 'w', 'utf-8') as cache_file:
            cache_file.write(_make_cache_from_cmp(parsed_ext))
    except Exception as err:
        mlogger.debug('Error writing cache...')
        raise PyRevitException('Error writing cache for: {} | {}'
                               .format(parsed_ext, err))


def update_cache(parsed_ext):
    mlogger.debug('Updating cache for tab: %s ...', parsed_ext.name)
    _write_cache_for(parsed_ext)
    mlogger.debug('Cache updated for tab: %s', parsed_ext.name)


def get_cached_extension(installed_ext):
    cached_ext_dict = _read_cache_for(installed_ext)
    # try:
    mlogger.debug('Constructing components from cache for: %s',
                    installed_ext)
    # get cached sub component dictionary and call recursive maker function
    _make_sub_cmp_from_cache(installed_ext,
                                cached_ext_dict.pop(gencomps.SUB_CMP_KEY))
    mlogger.debug('Load successful...')
    # except Exception as err:
    #     mlogger.debug('Error reading cache...')
    #     raise PyRevitException('Error creating ext from cache for: {} | {}'
    #                            .format(installed_ext.name, err))

    return installed_ext


def is_cache_valid(extension):
    try:
        cached_ext_dict = _read_cache_for(extension)  # type: dict
        mlogger.debug('Extension cache directory is: %s for: %s',
                      extension.directory, extension)
        cache_dir_valid = cached_ext_dict[gencomps.EXT_DIR_KEY] == extension.directory

        mlogger.debug('Extension cache version is: %s for: %s',
                      extension.pyrvt_version, extension)
        cache_version_valid = \
            cached_ext_dict[comps.EXT_HASH_VERSION_KEY] == extension.pyrvt_version

        mlogger.debug('Extension hash value is: %s for:%s',
                      extension.dir_hash_value, extension)
        cache_hash_valid = \
            cached_ext_dict[comps.EXT_HASH_VALUE_KEY] == extension.dir_hash_value

        cache_valid = \
            cache_dir_valid and cache_version_valid and cache_hash_valid

        # cache is valid if both version and hash value match
        return cache_valid

    except PyRevitException as err:
        mlogger.debug(err)
        return False

    except Exception as err:
        mlogger.debug('Error determining cache validity: %s | %s',
                      extension, err)
