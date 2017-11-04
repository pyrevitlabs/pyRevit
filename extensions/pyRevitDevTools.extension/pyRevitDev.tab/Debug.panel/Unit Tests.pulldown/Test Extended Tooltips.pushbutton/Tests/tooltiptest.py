import clr
clr.AddReference('AdWindows')

from System import Uri, UriKind
from System.Reflection import BindingFlags

import Autodesk.Windows as AdWindows

import pyrevit
from pyrevit.coreutils import ribbon

ui = ribbon.get_current_ui()
rb = ui.ribbon_tab('Tesla').ribbon_panel('General').ribbon_item('Tesla').get_rvtapi_object()
# meth = rb.GetType().GetMethod('get_ToolTip', BindingFlags.Public | BindingFlags.Instance)
# r = meth.Invoke(rb, None)

# tt = AdWindows.RibbonToolTip()
# tt.Title = "This is important button1"
# tt.ExpandedContent = "tooltip text"
# tt.ExpandedVideo = Uri('path/to/tooltip.swf')

# r.ExpandedVideo = Uri(r'C:\Users\eirannejad\AppData\Roaming\pyRevit\pyRevitDev\pyRevitDev\extensions\pyRevitDevTools.extension\pyRevitDev.tab\Debug.panel\Unit Tests.pulldown\Test Extended Tooltips.pushbutton\tooltip.swf')
# r.HelpSource = Uri('https://www.google.com/')
# r.HelpTopic = ''


tt = AdWindows.RibbonToolTip()
tt.HelpSource = Uri('https://www.google.com/')
tt.Title = "This is important button1"
tt.ExpandedContent = "tooltip text"
tt.ExpandedVideo = Uri(r'C:\Users\eirannejad\AppData\Roaming\pyRevit\pyRevitDev\pyRevitDev\extensions\pyRevitDevTools.extension\pyRevitDev.tab\Debug.panel\Unit Tests.pulldown\Test Extended Tooltips.pushbutton\tooltip.swf')

rb.ToolTip = tt
