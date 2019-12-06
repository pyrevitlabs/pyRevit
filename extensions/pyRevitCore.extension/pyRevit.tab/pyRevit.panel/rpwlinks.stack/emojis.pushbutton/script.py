"""Prints all available emojis with shorthand codes."""
from pyrevit.runtime.types import ScriptConsoleEmojis

from pyrevit import script

output = script.get_output()


__context__ = 'zero-doc'

output.freeze()
for e in ScriptConsoleEmojis.emojiDict.Keys:
    print(':{0}: : {0}'.format(e))
output.unfreeze()