import pyRevit.ui as ui

cui = ui.get_current_ui()

tab = cui.ribbon_tab('Annotate')
b = cui.ribbon_tab('Annotate').ribbon_panel('Symbol').ribbon_item('Symbol')

for tabs in cui:
    print tabs, tabs.name

for panel in cui.ribbon_tab('Systems'):
    print panel, panel.name

for item in cui.ribbon_tab('Systems').ribbon_panel('Electrical'):
    print item, item.name

panel = cui.ribbon_tab('Systems').ribbon_panel('Electrical')

p = panel._get_rvtapi_object()


fp = None

from Autodesk.Windows import *
for panel in cui.ribbon_tab('Systems'):
    for item in panel:
        if isinstance(item._get_rvtapi_object(), RibbonFoldPanel):
            fp = item
            
joe = set()

from Autodesk.Windows import *
for tab in [cui.ribbon_tab('Systems'), cui.ribbon_tab('Annotate')]:
    for panel in tab:
        for item in panel._get_rvtapi_object().Source.Items:
            joe.add(type(item))
            if isinstance(item, RibbonFoldPanel):
                fp = item

for i in joe:
    print i