"""Lists the selected element ids as clickable links. This is a quick way to go through a series of elements."""

from scriptutils import this_script
from revitutils import selection

this_script.output.set_width(200)

for idx, elid in enumerate(selection.element_ids):
    print('{}: {}'.format(idx+1, this_script.output.linkify(elid)))
