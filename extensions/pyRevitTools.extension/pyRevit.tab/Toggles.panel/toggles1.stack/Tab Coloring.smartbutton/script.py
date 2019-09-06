"""Does its best at visually separating open documents."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import re

from pyrevit import HOST_APP
from pyrevit.runtime.types import DocumentTabEventUtils
from pyrevit.coreutils.ribbon import ICON_MEDIUM
from pyrevit import script
from pyrevit.userconfig import user_config


__context__ = 'zero-doc'
__min_revit_ver__ = 2019


output = script.get_output()

COLOR_TAG_STYLE_TEMPLATE = \
    '.doc-color-tag{0} {{ '\
    'background-color: #{1}; '\
    'color: white; '\
    'padding: 1px 5px 1px 5px;'\
    ' }}'
COLOR_TAG_HTML_TEMPLATE = '<a title="{0}" class="doc-color-tag{1}">{0}</a>'


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    button_icon = script_cmp.get_bundle_file(
        'on.png' if user_config.colorize_docs else 'off.png'
        )
    ui_button_cmp.set_icon(button_icon, icon_size=ICON_MEDIUM)


# <System.Windows.Media.SolidColorBrush object at 0x0000000000001DE4 [#FF808080]>)

if __name__ == '__main__':
    if __shiftclick__: #pylint: disable=undefined-variable
        print("Active: %s" % DocumentTabEventUtils.IsUpdatingDocumentTabs)
        if DocumentTabEventUtils.DocumentBrushes:
            print("Count: %s" % DocumentTabEventUtils.DocumentBrushes.Count)
            index = 0
            for k, v in dict(DocumentTabEventUtils.DocumentBrushes).items():
                color = re.findall(r'\#(.+)\]', repr(v))[0].lower()[-6:]
                output.add_style(COLOR_TAG_STYLE_TEMPLATE.format(index, color))
                color_tag = COLOR_TAG_HTML_TEMPLATE.format(color, index)
                output.print_html(
                    'Doc Id: {} with {}'.format(str(k), color_tag)
                    )
                index += 1
    else:
        if DocumentTabEventUtils.IsUpdatingDocumentTabs:
            DocumentTabEventUtils.StopGroupingDocumentTabs()
        else:
            DocumentTabEventUtils.StartGroupingDocumentTabs(HOST_APP.uiapp)
        script.toggle_icon(DocumentTabEventUtils.IsUpdatingDocumentTabs)
