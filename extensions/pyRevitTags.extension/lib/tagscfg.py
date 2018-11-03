"""Config module for tags tools."""
#pylint: disable=E0401,W0703,C0103,W0123,W0603
from collections import namedtuple

from pyrevit.coreutils import logger
from pyrevit import revit

TAG_DELIMITER = ','
TAG_MODIFIER_DELIMITER = ' '
TAG_MODIFIER_MARKER = '/'
TAG_FILTER_NAMING = '{all_or_none} TAG {tag_names}'
TAG_PARAM_ID = 'doctag'
TAGVIEW_PREFIX = 'TAG_VIEW'
TAGS_MODIFS_COLOR_DEFAULT = '#909090'

CACHE_TAG_PARAM = None

mlogger = logger.get_logger(__name__)


TagModifierDef = namedtuple('TagModifierDef', ['abbrev', 'name', 'color'])


def _find_tags_param():
    for project_param in revit.query.get_project_parameters(doc=revit.doc):
        if TAG_PARAM_ID in project_param.name.lower():
            return project_param.name


def get_tags_param():
    global CACHE_TAG_PARAM
    if not CACHE_TAG_PARAM:
        CACHE_TAG_PARAM = _find_tags_param()

    return CACHE_TAG_PARAM


def get_modifier_defs():
    return [
        TagModifierDef(abbrev='IFF',
                       name='Issued for Fabrication',
                       color='#f39c12'),
        TagModifierDef(abbrev='IFC',
                       name='Issue For Construction',
                       color='#c7254e'),
        TagModifierDef(abbrev='IFR',
                       name='Issue For Review',
                       color='#a4cc00'),
        TagModifierDef(abbrev='ASBUILT',
                       name='As-Built Content',
                       color=TAGS_MODIFS_COLOR_DEFAULT),
        TagModifierDef(abbrev='NIC',
                       name='Not in Contract',
                       color='#1273fc'),
        TagModifierDef(abbrev='VIF',
                       name='Verified In Field',
                       color='#4f8b16'),
        ]


def verify_tags_configs():
    if not get_tags_param():
        mlogger.debug('Error verifying tags configuration.')
        return False
    return True
