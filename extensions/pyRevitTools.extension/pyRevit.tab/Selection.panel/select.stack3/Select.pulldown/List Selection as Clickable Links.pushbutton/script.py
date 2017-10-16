"""Lists the selected element ids as clickable links. This is a quick way to go through a series of elements."""

from pyrevit import script
from revitutils import selection

output = script.get_output()

if len(selection.element_ids) > 0:
	output.set_width(200)

	for idx, elid in enumerate(selection.element_ids):
		print('{}: {}'.format(idx+1, output.linkify(elid)))
