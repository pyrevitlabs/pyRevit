"""Config module for tags tools."""
#pylint: disable=E0401,W0703,C0103,W0123,W0603
from collections import namedtuple

from pyrevit import PyRevitException
from pyrevit import coreutils
from pyrevit.coreutils import logger
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit.userconfig import user_config

TAG_DELIMITER = ','
TAG_MODIFIER_DELIMITER = ' '
TAG_MODIFIER_MARKER = '/'
TAG_FILTER_NAMING = '{all_or_none} TAG {tag_names}'

TAGVIEW_PREFIX = 'TAG_VIEW'

TAGS_CONFIG_SECTION = 'Tags'

TAGS_MODIFS_CONFIG_SECTION = 'TagModifiers'
TAGS_MODIFS_COLOR_DEFAULT = '#909090'


mlogger = logger.get_logger(__name__)


CACHED_TAGS_PARAM = None
CACHED_TAGS_PARAM_LISTSECTION = None
CACHED_TAGS_SHARED_PARAM_FILE = None
CACHED_MODIFIERS_DEFS = []


TagModifierDef = namedtuple('TagModifierDef', ['abbrev', 'name', 'color'])


def update_tags_config():
    global CACHED_TAGS_PARAM
    global CACHED_TAGS_PARAM_LISTSECTION
    global CACHED_TAGS_SHARED_PARAM_FILE
    global CACHED_MODIFIERS_DEFS

    mlogger.debug('Looking up tags configs...')
    if user_config.has_section(TAGS_CONFIG_SECTION):
        cfgsection = user_config.get_section(TAGS_CONFIG_SECTION)

        # tags param
        CACHED_TAGS_PARAM = cfgsection.get_option('param', None)
        mlogger.debug('Tags parameter is %s', CACHED_TAGS_PARAM)
        if not CACHED_TAGS_PARAM:
            raise PyRevitException('Tags parameter is not configured.')

        # tags param list section
        CACHED_TAGS_PARAM_LISTSECTION = \
            cfgsection.get_option('paramlistsection', None)
        mlogger.debug('Tags param list section is %s',
                      CACHED_TAGS_PARAM_LISTSECTION)

        # tags shared param file
        CACHED_TAGS_SHARED_PARAM_FILE = \
            cfgsection.get_option('sharedparamfile', None)
        mlogger.debug('Tags param list section is %s',
                      CACHED_TAGS_SHARED_PARAM_FILE)

        mlogger.debug('Looking up tags modifiers configs...')

        CACHED_MODIFIERS_DEFS = []
        if user_config.has_section(TAGS_MODIFS_CONFIG_SECTION):
            modif_cfgsection = \
                user_config.get_section(TAGS_MODIFS_CONFIG_SECTION)
            for modif_cfg in modif_cfgsection.get_subsections():
                color = modif_cfg.get_option('color', TAGS_MODIFS_COLOR_DEFAULT)
                color = coreutils.format_hex_rgb(color)
                CACHED_MODIFIERS_DEFS.append(
                    TagModifierDef(
                        abbrev=modif_cfg.subheader,
                        name=modif_cfg.get_option('name', '??'),
                        color=color
                    )
                )
    else:
        mlogger.debug('Config section for tags tools not found: %s',
                      TAGS_CONFIG_SECTION)
        raise PyRevitException('Tags tools are not configured.')


def get_tags_param():
    global CACHED_TAGS_PARAM

    if not CACHED_TAGS_PARAM:
        update_tags_config()

    return CACHED_TAGS_PARAM


def get_modifier_defs():
    global CACHED_MODIFIERS_DEFS

    if not CACHED_MODIFIERS_DEFS:
        update_tags_config()

    return CACHED_MODIFIERS_DEFS


def verify_tags_configs():
    try:
        update_tags_config()
        revit.query.get_sharedparam_id(get_tags_param())
        return True
    except Exception:
        return False


def ensure_tag_param():
    tags_param = get_tags_param()
    # ensure_sharedparam_file()
    # try:
    #     with revit.Transaction('Setup {}'.format(tags_param)):
    #         res = revit.ensure.ensure_sharedparam(
    #             sparam_name=tags_param,
    #             sparam_categories=None,
    #             sparam_group=DB.BuiltInParameterGroup.PG_PHASING,
    #             allow_vary_betwen_groups=True,
    #             doc=revit.doc
    #             )
    #         forms.alert_ifnot(
    #             res,
    #             'Can not setup {} shared parameter. '
    #             'Make sure shared parameter file is '
    #             'setup correctly.'
    #             .format(tags_param),
    #             exit=True
    #             )
    # except Exception as param_load_err:
    #     mlogger.debug(
    #         'Error ensuring shared param: %s | %s',
    #         tags_param,
    #         getattr(param_load_err, 'msg', str(param_load_err))
    #         )
    #     return False

