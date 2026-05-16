"""Prints all available emojis with shorthand codes."""
#pylint: disable=import-error
from pyrevit.framework import Emojis

from pyrevit import script

output = script.get_output()


output.freeze()
for e in Emojis.Emojis.EmojiDict.Keys:
    print(':{0}: : {0}'.format(e))
output.unfreeze()
