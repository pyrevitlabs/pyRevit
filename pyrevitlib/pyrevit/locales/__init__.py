import gettext

from pyrevit import LOCALES_DIR

lang_code = 'fa'

lang = gettext.translation('base',
                           localedir=LOCALES_DIR,
                           languages=[lang_code])
lang.install()


def utf8_gettext(s):
    return lang.gettext(s).decode('utf-8')


_ = utf8_gettext
