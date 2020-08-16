"""Dev scripts configs"""

# ==============================================================================
# Configs
# ------------------------------------------------------------------------------
# supported versions
VERSION_RANGE = 2017, 2021

# binaries
BINPATH = "../bin/"

# root path for non-deployable source files
DEVPATH = "../dev/"
LABS = "./pyRevitLabs/pyRevitLabs.sln"
LOADERS = "./pyRevitLoader/pyRevitLoader.sln"
CPYTHONRUNTIME = (
    "./modules/pyRevitLabs.Python.Net/src/runtime/Python.Runtime.csproj"
)

# cli autocomplete files
USAGEPATTERNS = "./pyRevitLabs/pyRevitCLI/Resources/UsagePatterns.txt"
AUTOCOMP = "pyrevit-autocomplete.go"
AUTOCOMPBIN = BINPATH + "pyrevit-autocomplete.exe"

# telemetry server files
TELEMETRYSERVERPATH = "./pyRevitTelemetryServer/"
TELEMETRYSERVER = TELEMETRYSERVERPATH + "main.go"
TELEMETRYSERVERBIN = BINPATH + "pyrevit-telemetryserver.exe"

# python docs
DOCS_DIR = "../docs/"
DOCS_BUILD = DOCS_DIR + "_build/"
DOCS_INDEX = DOCS_BUILD + "index.html"

# release files
# API file paths must be absolute otherwise advancedinstaller will mess up
# the relative source paths defined inside the api file and fails
PYREVIT_AIPFILE = "../release/pyrevit.aip"
PYREVIT_CLI_AIPFILE = "../release/pyrevit-cli.aip"
PYREVIT_VERSION = ""
PYREVIT_VERSION_FILE = "../pyrevitlib/pyrevit/version"
PYREVIT_CLI_VERSION = ""

# data files
PYREVIT_HOSTS_DATAFILE = "../bin/pyrevit-hosts.json"
PYREVIT_PRODUCTS_DATAFILE = "../bin/pyrevit-products.json"

# files containing version definition
VERSION_FILES = [
    "./pyRevit/AssemblyVersion.cs",
    "../pyrevitlib/pyrevit/version",
]

# files containing copyright notice
COPYRIGHT_FILES = [
    "./pyRevit/AssemblyCopyright.cs",
    "../pyrevitlib/pyrevit/versionmgr/about.py",
    "../docs/conf.py",
]

# all source file locations that are part of pyRevit project
SOURCE_DIRS = [
    "../pyrevitlib/pyrevit",
    DEVPATH,
]
