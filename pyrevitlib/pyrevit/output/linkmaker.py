"""Handle creation of output window helper links."""

import json

from pyrevit import HOST_APP
from pyrevit.compat import safe_strtype
from pyrevit import DB
from pyrevit.coreutils.logger import get_logger


logger = get_logger(__name__)


PROTOCOL_NAME = 'revit://outputhelpers?'

DEFAULT_LINK = '<a title="Click to select or show element" ' \
                  'class="elementlink" {}>{}</a>'


def make_link(element_ids, contents=None):
    """Create link for given element ids.

    This link is a special format link with revit:// scheme that is handled
    by the output window to select the provided element ids in current project.
    Scripts should not call this function directly. Creating clickable element
    links is handled by the output wrapper object through the :func:`linkify`
    method.

    Example:
        >>> output = pyrevit.output.get_output()
        >>> for idx, elid in enumerate(element_ids):
        >>>     print('{}: {}'.format(idx+1, output.linkify(elid)))
    """
    elementquery = []
    if isinstance(element_ids, list):
        strids = [safe_strtype(x.IntegerValue) for x in element_ids]
    elif isinstance(element_ids, DB.ElementId):
        strids = [safe_strtype(element_ids.IntegerValue)]

    for strid in strids:
        elementquery.append('element[]={}'.format(strid))

    reviturl = '&'.join(elementquery)
    linkname = ', '.join(strids)

    if len(reviturl) >= 2000:
        alertjs = 'alert(&quot;Url was too long and discarded!&quot;);'
        linkattrs = 'href="#" onClick="{}"'.format(alertjs)
    else:
        linkattrs = 'href="{}{}{}"'.format(PROTOCOL_NAME,
                                           '&command=select&',
                                           reviturl)

    return DEFAULT_LINK.format(linkattrs, contents or linkname)
