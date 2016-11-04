def ui_test():
	import pyRevit.ui as ui
	cui = ui.get_current_ui()
	for tabs in cui:
		print tabs, tabs.name
	for panel in cui.ribbon_tab('Systems'):
		print panel, panel.name
	for item in cui.ribbon_tab('Systems').ribbon_panel('Electrical'):
		print item, item.AutomationName

	panel = cui.ribbon_tab('Systems').ribbon_panel('Electrical')
	p = panel._get_rvt_item()
