"""Dev scripts configs"""
import os.path as op


# ==============================================================================
# Configs
# ------------------------------------------------------------------------------
ROOT = op.dirname(op.dirname(op.dirname(__file__)))
# supported versions
VERSION_RANGE = 2017, 2021

# binaries
BINPATH = op.join(ROOT, "bin")
BINPATH_NETFX = op.join(BINPATH, "netfx")
BINPATH_NETCORE = op.join(BINPATH, "netcore")

LIBSPATH_NETFX = op.join(ROOT, "dev", "libs", "netfx")
LIBSPATH_NETCORE = op.join(ROOT, "dev", "libs", "netcore")

ENGINES2PATH_NETFX = op.join(ROOT, "bin", "netfx", "engines", "IPY2712PR")
ENGINES2PATH_NETCORE = op.join(ROOT, "bin", "netcore", "engines", "IPY2712PR")

ENGINES3PATH_NETFX = op.join(ROOT, "bin", "netfx", "engines", "IPY340PR")
ENGINES3PATH_NETCORE = op.join(ROOT, "bin", "netcore", "engines", "IPY340PR")

# root path for non-deployable source files
DEVPATH = op.join(ROOT, "dev")
RUNTIME = op.join(DEVPATH, "pyRevitLabs.PyRevit.Runtime/pyRevitLabs.PyRevit.Runtime.sln")
LABS = op.join(DEVPATH, "pyRevitLabs/pyRevitLabs.sln")
LABS_CLI = op.join(DEVPATH, "pyRevitLabs/pyRevitClI/pyRevitCLI.csproj")
LABS_DOCTOR = op.join(DEVPATH, "pyRevitLabs/pyRevitDoctor/pyRevitDoctor.csproj")
DEFAULT_IPY = op.join(DEVPATH, "modules/pyRevitLabs.IronPython2.sln")
LOADERS = op.join(DEVPATH, "pyRevitLoader/pyRevitLoader.sln")
CPYTHONRUNTIME = op.join(DEVPATH, "modules/pyRevitLabs.Python.Net/src/runtime/Python.Runtime.csproj")
DIRECTORY_BUILD_PROPS = op.join(DEVPATH, "Directory.Build.props")

# pyRevit deps
MAHAPPS = op.join(DEVPATH, "modules/pyRevitLabs.MahApps.Metro/src/MahApps.Metro/MahApps.Metro.csproj")
NEWTONSOFTJSON = op.join(DEVPATH, "modules/pyRevitLabs.Newtonsoft.Json/Src/Newtonsoft.Json/Newtonsoft.Json.csproj")
NLOG = op.join(DEVPATH, "modules/pyRevitLabs.NLog/src/NLog/NLog.csproj")

IRONPYTHON2 = op.join(DEVPATH, "modules/pyRevitLabs.IronPython2.sln")
IRONPYTHON2_LIB = op.join(DEVPATH, "modules/pyRevitLabs.IronPython2/Src/IronPython/IronPython.csproj")
IRONPYTHON2_MODULES = op.join(DEVPATH, "modules/pyRevitLabs.IronPython2/Src/IronPython.Modules/IronPython.Modules.csproj")
IRONPYTHON2_SQLITE = op.join(DEVPATH, "modules/pyRevitLabs.IronPython2/Src/IronPython.SQLite/IronPython.SQLite.csproj")
IRONPYTHON2_WPF = op.join(DEVPATH, "modules/pyRevitLabs.IronPython2/Src/IronPython.Wpf/IronPython.Wpf.csproj")

IRONPYTHON3 = op.join(DEVPATH, "modules/pyRevitLabs.IronPython3.sln")
IRONPYTHON3_LIB = op.join(DEVPATH, "modules/pyRevitLabs.IronPython3/Src/IronPython/IronPython.csproj")
IRONPYTHON3_MODULES = op.join(DEVPATH, "modules/pyRevitLabs.IronPython3/Src/IronPython.Modules/IronPython.Modules.csproj")
IRONPYTHON3_SQLITE = op.join(DEVPATH, "modules/pyRevitLabs.IronPython3/Src/IronPython.SQLite/IronPython.SQLite.csproj")
IRONPYTHON3_WPF = op.join(DEVPATH, "modules/pyRevitLabs.IronPython3/Src/IronPython.Wpf/IronPython.Wpf.csproj")

# cli autocomplete files
USAGEPATTERNS = op.join(
    DEVPATH, "pyRevitLabs/pyRevitCLI/Resources/UsagePatterns.txt"
)
AUTOCOMPPATH = "dev/pyRevitLabs/pyRevitCLIAutoComplete"
AUTOCOMP = op.join(AUTOCOMPPATH, "pyrevit-autocomplete.go")
AUTOCOMPBIN = op.join(BINPATH, "pyrevit-autocomplete.exe")

# telemetry server files
TELEMETRYSERVERPATH = op.join(DEVPATH, "pyRevitTelemetryServer")
TELEMETRYSERVER = op.join(TELEMETRYSERVERPATH, "main.go")
TELEMETRYSERVERBIN = op.join(BINPATH, "pyrevit-telemetryserver.exe")

# python docs
DOCS_DIR = op.join(ROOT, "docs")
DOCS_BUILD = op.join(DOCS_DIR, "_build")
DOCS_INDEX = op.join(DOCS_BUILD, "index.html")

# python module
PYREVIT_LIBS_PATH = op.join(ROOT, "pyrevitlib")
PYREVIT_MODULE_PATH = op.join(PYREVIT_LIBS_PATH, "pyrevit")

# release files
# API file paths must be absolute otherwise advancedinstaller will mess up
# the relative source paths defined inside the api file and fails
PYREVIT_UPGRADE_CODE = "92cd1cdd-85c6-438f-ad0a-67b08d59cc41"
PYREVIT_CLI_UPGRADE_CODE = "618520c4-0c3a-4e8d-8e8a-b74db3f3592b"

DISTRIBUTE_PATH = op.join(ROOT, "dist")
RELEASE_PATH = op.join(ROOT, "release")
PYREVIT_INSTALLERFILE = op.join(RELEASE_PATH, "pyrevit.iss")
PYREVIT_ADMIN_INSTALLERFILE = op.join(RELEASE_PATH, "pyrevit-admin.iss")
PYREVIT_CLI_INSTALLERFILE = op.join(RELEASE_PATH, "pyrevit-cli.iss")
PYREVIT_ADMIN_CLI_INSTALLERFILE = op.join(RELEASE_PATH, "pyrevit-cli-admin.iss")
PYREVIT_INSTALLER_FILES = [
    PYREVIT_INSTALLERFILE,
    PYREVIT_ADMIN_INSTALLERFILE,
]
PYREVIT_CLI_INSTALLER_FILES = [
    PYREVIT_CLI_INSTALLERFILE,
    PYREVIT_ADMIN_CLI_INSTALLERFILE,
]
INSTALLER_FILES = [
    PYREVIT_INSTALLERFILE,
    PYREVIT_CLI_INSTALLERFILE,
    PYREVIT_ADMIN_INSTALLERFILE,
    PYREVIT_ADMIN_CLI_INSTALLERFILE,
]

# msi installers
PYREVIT_COMMON_MSI_PROPSFILE = op.join(RELEASE_PATH, "pyrevit-common.props")
PYREVIT_CLI_MSI_PROPSFILE = op.join(RELEASE_PATH, "pyrevit-cli.props")
PYREVIT_CLI_MSI_INSTALLERFILE = op.join(RELEASE_PATH, "pyrevit-cli.wixproj")
PYREVIT_MSI_PROPS_FILES = [
]
PYREVIT_MSI_INSTALLER_FILES = [
]

PYREVIT_CLI_MSI_PROPS_FILES = [
    PYREVIT_CLI_MSI_PROPSFILE,
]
PYREVIT_CLI_MSI_INSTALLER_FILES = [
    PYREVIT_CLI_MSI_INSTALLERFILE,
]
MSI_PROPS_FILES = [
    PYREVIT_CLI_MSI_PROPSFILE,
]
MSI_INSTALLER_FILES = [
    PYREVIT_CLI_MSI_INSTALLERFILE,
]

PYREVIT_INSTALLER_NAME = "pyRevit_{version}_signed"
PYREVIT_ADMIN_INSTALLER_NAME = "pyRevit_{version}_admin_signed"
PYREVIT_CLI_INSTALLER_NAME = "pyRevit_CLI_{version}_signed"
PYREVIT_CLI_ADMIN_INSTALLER_NAME = "pyRevit_CLI_{version}_admin_signed"

INSTALLER_EXES = [
    op.join(DISTRIBUTE_PATH, PYREVIT_INSTALLER_NAME),
    op.join(DISTRIBUTE_PATH, PYREVIT_ADMIN_INSTALLER_NAME),
    op.join(DISTRIBUTE_PATH, PYREVIT_CLI_INSTALLER_NAME),
    op.join(DISTRIBUTE_PATH, PYREVIT_CLI_ADMIN_INSTALLER_NAME),
]

INSTALLER_MSIS = [
    op.join(DISTRIBUTE_PATH, PYREVIT_CLI_ADMIN_INSTALLER_NAME),
]

# choco files
PYREVIT_CHOCO_NUSPEC_FILE = op.join(RELEASE_PATH, "choco", "pyrevit-cli.nuspec")
PYREVIT_CHOCO_INSTALL_FILE = op.join(
    RELEASE_PATH, "choco/tools", "chocolateyinstall.ps1"
)
PYREVIT_CHOCO_NUPKG_NAME = "pyrevit-cli.{version}.nupkg"
PYREVIT_CHOCO_NUPKG_FILE = op.join(DISTRIBUTE_PATH, PYREVIT_CHOCO_NUPKG_NAME)

PYREVIT_WIP_VERSION_EXT = "-wip"
PYREVIT_VERSION_FILE = op.join(PYREVIT_MODULE_PATH, "version")
PYREVIT_INSTALL_VERSION_FILE = op.join(RELEASE_PATH, "version")

# data files
PYREVIT_HOSTS_DATAFILE = op.join(BINPATH, "pyrevit-hosts.json")
PYREVIT_PRODUCTS_DATAFILE = op.join(BINPATH, "pyrevit-products.json")

# files containing version definition
VERSION_FILES = [
    DIRECTORY_BUILD_PROPS,
    PYREVIT_VERSION_FILE,
]

# files containing copyright notice
COPYRIGHT_FILES = [
    DIRECTORY_BUILD_PROPS,
    op.join(PYREVIT_MODULE_PATH, "versionmgr/about.py"),
    # op.join(DOCS_DIR, "conf.py"),# not used by new documentation workflow
    op.join(ROOT, "README.md"),
    PYREVIT_INSTALLERFILE,
    PYREVIT_CLI_INSTALLERFILE,
    PYREVIT_ADMIN_INSTALLERFILE,
    PYREVIT_ADMIN_CLI_INSTALLERFILE,
]

COMMIT_FILES = [
    AUTOCOMP,
    DIRECTORY_BUILD_PROPS,
    PYREVIT_VERSION_FILE,
    op.join(PYREVIT_MODULE_PATH, "versionmgr/about.py"),
    op.join(DOCS_DIR, "conf.py"),
    op.join(ROOT, "README.md"),
    r"release\*",
    r"bin\*",
]

# all source file locations that are part of pyRevit project
SOURCE_DIRS = [
    PYREVIT_MODULE_PATH,
    DEVPATH,
]

# all extensions
EXTENSIONS_PATH = op.join(ROOT, "extensions")
