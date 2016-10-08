# import os
# from os import path
# from tempfile import gettempdir

# from System.Diagnostics import Process

# from loader.logger import logger

# ROOT_DIR = os.getcwd()
# SCRIPTS_DIR = ROOT_DIR
# TEMPDIR = gettempdir()
# LOADER = path.join(SCRIPTS_DIR, '__init__.py')

# # Revit Python Loader Assmebly name and CmdLoader Class
# ASSEMBLY_NAME = 'pyRevitLoader'
# CMD_LOADER_BASE = 'pyRevitLoader.CommandLoaderBase'
# # Name for Scripts DLL
# SCRIPTS_DLL_BASENAME = 'pyrevit_assembly'

# # Unique Per Session
# # SESSION_ID = '{}_session{}'.format(SCRIPTS_DLL_BASENAME,str(Process.GetCurrentProcess().Id))
# CACHE_FILE = '{}_cache'.format(SCRIPTS_DLL_BASENAME)
# logger.info('CWD is {}'.format(ROOT_DIR))

# PKG_IDENTIFIER = '.pkg'


# # pyrevit.tab\PkgMager
# PKGMGR_DIR = os.path.dirname(__file__)

# # pyRevit\pyRevit\pyRevit.tab\
# SCRIPTS_DIR = os.path.dirname(PKGMGR_DIR)

# # pyRevit\pyRevit - this is where pyRevit.tab is
# PYREVIT_DIR = os.path.dirname(SCRIPTS_DIR)

# #  Path fir file version of packages.json
# PKGSJSON_FILEPATH = os.path.join(PKGMGR_DIR, 'packages.json')

# # CHANGE TO PYREVIT REPO
# PKGSJSON_WEB = 'https://raw.githubusercontent.com/gtalarico/pyRevit/pyrevitv3/pyRevit/pyRevit.tab/pkgManager/packages.json'

# #  Very unecessary
# BREAKLINE = '=' * 40

# # Where __git__and __init__ are
# ROOT_DIR = os.path.dirname(PYREVIT_DIR)

# #  Get Git Location
# # PYREVIT_ROOT_DIR = os.path.dirname(PYREVIT_DIR)
# # GIT_EXE = os.path.join(ROOT'__git__', 'cmd', 'git.exe')
# GIT_EXE = os.path.join('__git__', 'cmd', 'git.exe')

# # Changes to directory to root pyrevit dir, so cloned scripts will land there
# os.chdir(ROOT_DIR)
# CWD = os.getcwd()
