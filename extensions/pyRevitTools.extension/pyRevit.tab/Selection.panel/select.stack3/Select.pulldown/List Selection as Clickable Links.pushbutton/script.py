"""Lists the selected element ids as clickable links. This is a quick way to go through a series of elements."""

from scriptutils import this_script
from revitutils import selection

this_script.output.set_width(200)

for elid in selection.element_ids:
    print(this_script.output.linkify(elid))
