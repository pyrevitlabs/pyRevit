import os


# pyrevit.tab\PkgMager
PKGMGR_DIR = os.path.dirname(__file__)

# pyrevit\pyrevit\pyrevit.tab\
SCRIPTS_DIR = os.path.dirname(PKGMGR_DIR)

# pyrevit\pyrevit - this is where pyrevit.tab is
PYREVIT_DIR = os.path.dirname(SCRIPTS_DIR)

#  Path fir file version of extensions.json
PKGSJSON_FILEPATH = os.path.join(PKGMGR_DIR, 'extensions.json')

# CHANGE TO PYREVIT REPO
PKGSJSON_WEB = 'https://raw.githubusercontent.com/gtalarico/pyrevit/pyrevitv3/pyrevit/pyrevit.tab/pkgManager/extensions.json'

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
