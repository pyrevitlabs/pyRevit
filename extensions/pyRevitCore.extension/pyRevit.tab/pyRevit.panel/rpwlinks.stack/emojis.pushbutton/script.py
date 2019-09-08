"""Prints all available emojis with shorthand codes."""
from pyrevit.runtime.types import ScriptOutputEmojis

from pyrevit import script

output = script.get_output()


__context__ = 'zero-doc'

output.freeze()
for e in ScriptOutputEmojis.emojiDict.Keys:
    print(':{0}: : {0}'.format(e))
output.unfreeze()