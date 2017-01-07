__doc__ = 'Add or remove pyRevit extensions.'

from scriptutils import logger
from pyrevit.plugins import extpackages


logger.info('----------------------- WORK IN PROGRESS ---------------------------')


for plugin_ext in extpackages.get_ext_packages():
    print """Extension:
    {name}
    Type: {type}
    {description}

    Extension git repo: {url}
    Extension website: {website}
    Extension image: {image}


    """.format(type=plugin_ext.type,
               name=plugin_ext.name,
               description=plugin_ext.description,
               url=plugin_ext.url,
               website=plugin_ext.website,
               image=plugin_ext.image)
