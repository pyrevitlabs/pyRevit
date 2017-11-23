import json

from pyrevit import HOST_APP
from pyrevit import DB
from pyrevit.coreutils.logger import get_logger


logger = get_logger(__name__)


PROTOCOL_NAME = 'revit://select?'

DEFAULT_LINK = '<a title="Click to select or show element" ' \
               'style="background-color: #f5f7f2; ' \
               'font-size:8pt; ' \
               'color: #649417; ' \
               'border: 1px solid #649417; ' \
               'border-radius:3px; ' \
               'vertical-align:middle; '\
               'margin:-4,0,-4,0; ' \
               'margin: 2px; ' \
               'padding: 1px 4px; ' \
               'text-align: center; ' \
               'text-decoration: none; ' \
               'display: inline-block;" href="{0}{1}">{2}</a>'


def make_url(element_ids):
    elementquery = []
    if isinstance(element_ids, list):
        strids = [str(x.IntegerValue) for x in element_ids]
    elif isinstance(element_ids, DB.ElementId):
        strids = [str(element_ids.IntegerValue)]

    for strid in strids:
        elementquery.append('element[]={}'.format(strid))

    return DEFAULT_LINK.format(PROTOCOL_NAME,
                               '&'.join(elementquery),
                               ', '.join(strids))
