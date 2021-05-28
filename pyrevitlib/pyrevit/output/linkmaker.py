"""Handle creation of output window helper links."""

from pyrevit.compat import safe_strtype
from pyrevit import DB
from pyrevit.coreutils.logger import get_logger


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


PROTOCOL_NAME = 'revit://outputhelpers?'
LINK_SHOW_ICON = \
    'M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,' \
    '14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,' \
    '16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,' \
    '9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z'
DEFAULT_LINK = '<span>' \
               '<a class="elementlink" ' \
                  'style="margin-right:0px;padding-right:3px" ' \
                  'title="Click to select or show element" ' \
                  '{attrs_select} >' \
                     '{ids}' \
               '</a>' \
               '<a class="elementlink" ' \
                  'style="margin-left:0px;padding-left:3px" ' \
                  '{attrs_show}>' \
                     '<svg width="14" height="14" viewBox="2 2 20 20" >' \
                        '<path fill="white" d="{show_icon}" />' \
                     '</svg>' \
               '</a>' \
               '</span>'


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
    link_title = ', '.join(strids)

    if len(reviturl) >= 2000:
        alertjs = 'alert(&quot;Url was too long and discarded!&quot;);'
        linkattrs_select = 'href="#" onClick="{}"'.format(alertjs)
        linkattrs_show = linkattrs_select
    else:
        linkattrs_select = \
            'href="{}{}{}&show=false"'.format(PROTOCOL_NAME,
                                              '&command=select&',
                                              reviturl)
        linkattrs_show = linkattrs_select.replace('&show=false', '&show=true')

    return DEFAULT_LINK.format(
        attrs_select=linkattrs_select,
        attrs_show=linkattrs_show,
        ids=contents or link_title,
        show_icon=LINK_SHOW_ICON
        )
