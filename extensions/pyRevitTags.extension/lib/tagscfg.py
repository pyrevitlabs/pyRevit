"""Config module for tags tools."""

TAG_DELIMITER = ','
TAG_MODIFIER_DELIMITER = ' '
TAG_MODIFIER_MARKER = '/'
TAG_FILTER_NAMING = '{all_or_none} TAG {tag_names}'

TAGVIEW_PREFIX = 'TAG_VIEW'


def get_tags_param():
    return 'TAGS_PARAM'


def ensure_tag_param():
    pass
