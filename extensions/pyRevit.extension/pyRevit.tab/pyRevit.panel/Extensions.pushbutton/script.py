__doc__ = 'Add or remove pyRevit extensions.'

from scriptutils import logger
from pyrevit.plugins import extpackages


logger.info('----------------------- WORK IN PROGRESS ---------------------------')


for plugin_ext in extpackages.get_ext_packages():
    print """Extension:
    {name}
    {description}

    Extension git repo: {url}
    Extension website: {website}
    Extension website: {image}


    """.format(**plugin_ext)
