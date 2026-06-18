# pylint: skip-file
from pyrevit import script

output = script.get_output()

output.print_html(
    '<a href="revit://outputhelpers?command=print&message=Hello%20World" '
    'style="display:inline-block;text-decoration:none;font:inherit;'
    'padding:4px 10px;border:1px solid #8a8f94;'
    'background:#f5f6f7;color:#233749;">Print Hello World</a>'
)
