"""Developer example: a checkbox whose handlers come from a shared module.

Shared A and Shared B both import their handlers from
lib/devtools_checkbox_handlers.py in this panel. Each still saves its own
state and keeps its own change count, which the handler shows in the
checkbox's label.
"""

from devtools_checkbox_handlers import init as __chk_init__
from devtools_checkbox_handlers import on_change as __chk_on_change__
