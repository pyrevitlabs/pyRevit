"""Provides emoji support for the html-based output window.

Example:
    >>> from pyrevit.coreutils import emoji
    >>> emoji.emojize('Job completed :thumbs_up:')
    'Job completed <span><img src="./1F44D.png" class="emoji"></span>'
"""

import os.path as op
import re

from pyrevit.coreutils import prepare_html_str
from pyrevit.coreutils.emoji.unicodes import emoji_file_dict

HTML_EMOJI_SPAN = prepare_html_str('<span><img src="{}" class="emoji"></span>')


def emojize(text):
    """Replace all emoji shorthands with unicode image html tags.

    Args:
        text (str): string containing emoji shorthands

    Returns:
        str: string with shorthands replaces with html tags

    Example:
        >>> emojize('Job completed :thumbs_up:')
        'Job completed <span><img src="./1F44D.png" class="emoji"></span>'
    """
    pattern = re.compile(':([a-z0-9+-_]+):')

    def emojifier(match):
        emoji_name = match.group(1)
        if emoji_name in emoji_file_dict:
            emoji_name = emoji_file_dict[emoji_name]
            return HTML_EMOJI_SPAN.format(op.join(op.dirname(__file__),
                                                  'png',
                                                  '{}.png'.format(emoji_name)))
        else:
            return ':{}:'.format(emoji_name)

    return pattern.sub(emojifier, text)
