# -*- coding: utf-8 -*-
"""Verify stdout, every logger level, output ordering, and tracebacks render.

Exercises the buffered output path with a rapid stdout batch, each logger level,
interleaved print/logger/print_html to check ordering, emoji and wide unicode, a
trailing error-level log, and finally an uncaught exception. A correct run shows
every section in the order below, then the full IronPython traceback.
"""
from pyrevit import script

output = script.get_output()
logger = script.get_logger()
output.set_title('Log Output Test - IronPython')

# Rapid, un-delayed writes exercise the batched stdout path.
LINE_COUNT = 12
for num in range(1, LINE_COUNT + 1):
    print('flush-test line {} of {}'.format(num, LINE_COUNT))

# Each level renders with its own styling. error/critical are styled log records
# on the normal path, not the red traceback block; debug shows only in debug mode.
logger.debug('debug level (visible only in debug mode)')
logger.info('info level')
logger.success('success level')
logger.warning('warning level')
logger.error('error level (styled log, not a traceback)')
logger.critical('critical level')
logger.deprecate('deprecate level')

# print, logger, and print_html travel different output paths; the rendered
# order must match the emission order below.
print('order 1 of 4: print')
logger.warning('order 2 of 4: logger')
output.print_html('<b>order 3 of 4: print_html</b>')
print('order 4 of 4: print')

# Emoji shortcodes and wide unicode must survive the buffered path intact.
print('emoji :thumbs_up: :OK_hand: wide 结构结构 end')

# A trailing error-level log must still reach the window at teardown.
logger.error('trailing error log must be visible')

print('all sections above must be visible, then a full traceback below.')

# Uncaught on purpose: exercises the error path, not print/logging.
raise RuntimeError('intentional test traceback - its full body must be visible')
