from pyrevit import script


uifile = script.get_bundle_file('ui.html')
output = script.get_output()

output.show()
output.open_url('file:///' + uifile)
