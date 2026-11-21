"""Developer example: the second checkbox that shares Shared A's handlers.

Both checkboxes import their handlers from lib/devtools_checkbox_handlers.py
in this panel. script.get_config() and ctx.user_data still belong to the
checkbox that changed, so the two never mix their state or their counts.
"""

from devtools_checkbox_handlers import init as __chk_init__
from devtools_checkbox_handlers import on_change as __chk_on_change__
