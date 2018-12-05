"""Unit Tests for pyrevit.coreutils module."""


__context__ = 'zerodoc'


import pyrevit.unittests as prtests

prtests.perform_coreutils_tests()



from pyrevit import script

output = script.get_output()

# use output object to add a CSS style to browser DOM
style = """
.legendblue {
   color: Blue;
}

.legendred {
   color: Red;
}

.legendgreen {
   color: Green;
}
"""

output.add_style(style)

output.print_html('<div class="legendblue">Legend Text</div>')
output.print_html('<div class="legendred">Legend Red</div>')
output.print_html('<div class="legendgreen">Legend Green</div>')
