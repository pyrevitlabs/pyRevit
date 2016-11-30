import sys
import logging

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(levelname)s| %(message)s [%(module)s:%(lineno)d]")
# formatter = logging.Formatter("%(levelname)s| %(message)s [%(module)s/%(funcName)s/%(lineno)d")
handler.setFormatter(formatter)

logger = logging.getLogger('pyrevit-pkgmanager')
logger.addHandler(handler)
logger.setLevel(logging.INFO)
