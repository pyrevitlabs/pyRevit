import re
import os.path as op

from pyrevit.core.emoji.code import emoji_file_dict

html_emoji_span = '<span><img src="{}" style="margin-top:0.35em;margin-bottom:-0.35em;"></span>'


def emojize(text):
    pattern = re.compile(':([a-z0-9+-_]+):')

    def emojifier(match):
        emoji_name = match.group(1)
        if emoji_name in emoji_file_dict:
            emoji_name = emoji_file_dict[emoji_name]

        return html_emoji_span.format(op.join(op.dirname(__file__), 'png', '{}.png'.format(emoji_name)))

    return pattern.sub(emojifier, text)
