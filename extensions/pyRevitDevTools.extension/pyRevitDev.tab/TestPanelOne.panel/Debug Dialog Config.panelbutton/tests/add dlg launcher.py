from System.Reflection import BindingFlags

from pyrevit.api import AdWindows as ad
from pyrevit import UI
from pyrevit.coreutils import ribbon

ui = ribbon.get_current_ui()

rp = ad.RibbonPanel()
rps = ad.RibbonPanelSource()
rp.Source = rps
rps.Title = 'Test Panel'

t = ui.ribbon_tab('pyRevitDev')
rt = t.get_rvtapi_object()
rt.Panels.Add(rp)

dlb = ad.RibbonButton()
dlb.Name = "TestCommand"
rps.Items.Add(dlb)

bbb = ui.ribbon_tab('pyRevitDev').ribbon_panel('Debug').ribbon_item('Logs')
brb = bbb.get_adwindows_object()
brbb = brb.Clone()
rps.DialogLauncher = brbb

rps.Items.Add(brb)

for panel in rt.Panels:
    if panel.Source.Title == 'Debug':
        panel.Source.DialogLauncher = brbb
