# -*- coding: utf-8 -*-
OPTION_DEFAULTS = [
    ("exclude_nested", True),
    ("only_current_view", True),
    ("reverse_filter", False),
]


def load_options(config):
    return {key: config.get_option(key, default) for key, default in OPTION_DEFAULTS}


def save_options(config, options):
    for key, default in OPTION_DEFAULTS:
        config.set_option(key, options.get(key, default))
