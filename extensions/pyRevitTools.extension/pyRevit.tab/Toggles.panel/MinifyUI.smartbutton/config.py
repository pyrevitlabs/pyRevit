"""Minify UI tool config"""
#pylint: disable=E0401,C0103
from pyrevit import script

import minifyui

config = script.get_config()


minifyui.config_minifyui(config)
minifyui.update_ui(config)
