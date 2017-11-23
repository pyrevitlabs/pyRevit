import json

from pyrevit import HOST_APP
from pyrevit import DB
from pyrevit.coreutils.logger import get_logger


logger = get_logger(__name__)


PROTOCOL_NAME = 'revit://select?'

DEFAULT_LINK = '<a title="Click to select or show element" ' \
                  'class="elementlink" {}>{}</a>'


def make_link(element_ids):
    elementquery = []
    if isinstance(element_ids, list):
        strids = [str(x.IntegerValue) for x in element_ids]
    elif isinstance(element_ids, DB.ElementId):
        strids = [str(element_ids.IntegerValue)]

    for strid in strids:
        elementquery.append('element[]={}'.format(strid))

    reviturl = '&'.join(elementquery)
    linkname = ', '.join(strids)

    if len(reviturl) >= 2000:
        alertjs = 'alert(&quot;Url was too long and discarded!&quot;);'
        linkattrs = 'href="#" onClick="{}"'.format(alertjs)
    else:
        linkattrs = 'href="{0}{1}"'.format(PROTOCOL_NAME, reviturl)

    return DEFAULT_LINK.format(linkattrs, linkname)
