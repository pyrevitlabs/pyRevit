import os


# pyrevit.tab\PkgMager
PKGMGR_DIR = os.path.dirname(__file__)

# pyRevit\pyRevit\pyRevit.tab\
SCRIPTS_DIR = os.path.dirname(PKGMGR_DIR)

# pyRevit\pyRevit - this is where pyRevit.tab is
PYREVIT_DIR = os.path.dirname(SCRIPTS_DIR)

#  Path fir file version of packages.json
PKGSJSON_FILEPATH = os.path.join(PKGMGR_DIR, 'packages.json')

# CHANGE TO PYREVIT REPO
PKGSJSON_WEB = 'https://raw.githubusercontent.com/gtalarico/pyRevit/pyrevitv3/pyRevit/pyRevit.tab/pkgManager/packages.json'

# .Ico path
ICO_FILEPATH = os.path.join(PKGMGR_DIR, 'pkgManager.ico')

#  Very unecessary
BREAKLINE = '=' * 40

# Where __git__and __init__ are
ROOT_DIR = os.path.dirname(PYREVIT_DIR)

#  Get Git Location
# PYREVIT_ROOT_DIR = os.path.dirname(PYREVIT_DIR)
# GIT_EXE = os.path.join(ROOT'__git__', 'cmd', 'git.exe')
GIT_EXE = os.path.join('__git__', 'cmd', 'git.exe')

# Changes to directory to root pyrevit dir, so cloned scripts will land there
os.chdir(ROOT_DIR)
CWD = os.getcwd()
