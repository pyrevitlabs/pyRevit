__doc__ = 'Add or remove pyRevit extensions.'

import os
import os.path as op
import json

from pyrevit.userconfig import user_config

ext_dirs = user_config.get_ext_root_dirs()

ext_def_dict = {'extensions':[]}

for ext_dir in ext_dirs:
    ext_def_file = op.join(ext_dir, 'extensions.json')
    if op.exists(ext_def_file):
        with open(ext_def_file, 'r') as ext_def:
            ext_def_dict['extensions'].extend(json.load(ext_def)['extensions'])

for ext in ext_def_dict['extensions']:
    print """Extension:
    {name}
    {description}

    Extension git repo: {url}
    Extension website: {website}
    Extension website: {image}


    """.format(**ext)
