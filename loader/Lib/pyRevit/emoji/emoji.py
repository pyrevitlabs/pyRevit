import re
import os.path as op

from .code import emojiFileNameDict

from ..config import LOADER_ASM_DIR


html_emoji_span = '<span><img src="{}" style="width:20px;margin-bottom:-0.35em;"></span>'


def emojize(text):
    pattern = re.compile('(:[a-z0-9\+\-_]+:)')

    def emorepl(match):
        value = match.group(1)

        if value in emojiFileNameDict:
            return html_emoji_span.format(op.join(LOADER_ASM_DIR,
                                                  'Emojis\{}.png'.format(emojiFileNameDict[value])))

    return pattern.sub(emorepl, text)

