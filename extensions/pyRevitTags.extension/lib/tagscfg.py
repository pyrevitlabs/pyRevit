"""Config module for tags tools."""
#pylint: disable=E0401,W0703,C0103,W0123
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
TAGS_CONFIG_MODIFIER_NAME_KEY = 'name'
TAGS_CONFIG_MODIFIER_COLOR_KEY = 'color'
TAGS_CONFIG_MODIFIER_COLOR_DEFAULT = '#909090'

mlogger = logger.get_logger(__name__)


def get_tags_param():
    user_config.reload()
    if user_config.has_section(TAGS_CONFIG_SECTION):
        cfgsection = user_config.get_section(TAGS_CONFIG_SECTION)
        if cfgsection:
            return cfgsection.param


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


def get_modifiers_cfgdict():
    user_config.reload()
    if user_config.has_section(TAGS_CONFIG_SECTION):
        cfgsection = user_config.get_section(TAGS_CONFIG_SECTION)
        if cfgsection:
            return cfgsection.modifiers
