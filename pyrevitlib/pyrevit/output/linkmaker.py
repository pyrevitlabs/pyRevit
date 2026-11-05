"""Handle creation of output window helper links."""

from pyrevit.compat import safe_strtype, get_elementid_value_func
from pyrevit.coreutils.logger import get_logger


# pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


PROTOCOL_NAME = "revit://outputhelpers?"
MAX_INLINE_QUERY_LENGTH = 2000
# ctrl+click adds the link's elements to the
# current selection instead of replacing it
APPEND_SELECTION_ONCLICK = (
    'onclick="var appendEvt=window.event||event;'
    "var appendLnk=this;"
    "if(appendEvt.ctrlKey){"
    "location.href=this.href+'&append=true';"
    "setTimeout(function(){appendLnk.style.backgroundColor=&quot;#f39c12&quot;;},0);"
    'return false;}return true;"'
)
LINK_SHOW_ICON = (
    "M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,"
    "14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,"
    "16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,"
    "9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z"
)
DEFAULT_LINK = (
    "<span>"
    '<a class="elementlink" '
    'style="margin-right:0px;padding-right:3px" '
    'title="Click to select or show element" '
    "{attrs_select} >"
    "{ids}"
    "</a>"
    '<a class="elementlink" '
    'style="margin-left:0px;padding-left:3px" '
    "{attrs_show}>"
    '<svg width="14" height="14" viewBox="2 2 20 20" >'
    '<path fill="white" d="{show_icon}" />'
    "</svg>"
    "</a>"
    "</span>"
)


def make_link(element_ids, contents=None, register_ids=None):
    """Create link for given element ids.

    This link is a special format link with revit:// scheme that is handled
    by the output window to select the provided element ids in current project.
    Scripts should not call this function directly. Creating clickable element
    links is handled by the output wrapper object through the :func:`linkify`
    method.

    Ids that fit in a url (under :data:`MAX_INLINE_QUERY_LENGTH` characters) are
    embedded in the link itself. Longer lists are handed to ``register_ids`` and
    the link carries the token it returns, so any number of elements can be
    selected with one link.

    Args:
        element_ids (ElementId | list[ElementId]): single or multiple ids
        contents (str): label of the link. defaults to the list of ids, or to
            the element count when the ids are registered
        register_ids (callable): receives the comma separated id values and
            returns the token the output window resolves back to them. Only
            called when the ids do not fit in the url

    Raises:
        ValueError: when an item is not an ElementId, or the ids do not fit in
            the url and no ``register_ids`` was given

    Examples:
        ```python
        output = pyrevit.output.get_output()
        for idx, elid in enumerate(element_ids):
            print('{}: {}'.format(idx+1, output.linkify(elid)))
        ```
    """
    get_elementid_value = get_elementid_value_func()
    try:
        try:
            strids = [safe_strtype(get_elementid_value(x)) for x in element_ids]
        except TypeError:
            strids = [safe_strtype(get_elementid_value(element_ids))]
    except AttributeError:
        raise ValueError("One or more items are not ElementIds")

    elementquery = ("element[]={}".format(strid) for strid in strids)

    reviturl = "&".join(elementquery)
    link_title = ", ".join(strids)

    if len(reviturl) >= MAX_INLINE_QUERY_LENGTH:
        if register_ids is None:
            raise ValueError(
                "{} element ids do not fit in one link and no register_ids "
                "was given".format(len(strids))
            )
        reviturl = "elements={}".format(register_ids(",".join(strids)))
        link_title = "{} elements".format(len(strids))

    base_link = 'href="{}{}{}&show={{}}"'.format(
        PROTOCOL_NAME, "&command=select&", reviturl
    )
    linkattrs_select = base_link.format("false") + " " + APPEND_SELECTION_ONCLICK
    linkattrs_show = base_link.format("true") + " " + APPEND_SELECTION_ONCLICK

    return DEFAULT_LINK.format(
        attrs_select=linkattrs_select,
        attrs_show=linkattrs_show,
        ids=contents or link_title,
        show_icon=LINK_SHOW_ICON,
    )
