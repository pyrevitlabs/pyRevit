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

# root path for non-deployable source files
DEVPATH = op.join(ROOT, "dev")
LABS = op.join(DEVPATH, "pyRevitLabs/pyRevitLabs.sln")
LOADERS = op.join(DEVPATH, "pyRevitLoader/pyRevitLoader.sln")
CPYTHONRUNTIME = op.join(
    DEVPATH, "modules/pyRevitLabs.Python.Net/src/runtime/Python.Runtime.csproj"
)

# cli autocomplete files
USAGEPATTERNS = op.join(DEVPATH, "pyRevitLabs/pyRevitCLI/Resources/UsagePatterns.txt")
AUTOCOMP = "pyrevit-autocomplete.go"
AUTOCOMPBIN = op.join(BINPATH, "pyrevit-autocomplete.exe")

# telemetry server files
TELEMETRYSERVERPATH = op.join(DEVPATH, "pyRevitTelemetryServer")
TELEMETRYSERVER = op.join(TELEMETRYSERVERPATH, "main.go")
TELEMETRYSERVERBIN = op.join(BINPATH, "pyrevit-telemetryserver.exe")

# python docs
DOCS_DIR = op.join(ROOT, "docs")
DOCS_BUILD = op.join(DOCS_DIR, "_build")
DOCS_INDEX = op.join(DOCS_BUILD, "index.html")

# release files
# API file paths must be absolute otherwise advancedinstaller will mess up
# the relative source paths defined inside the api file and fails
RELEASE_PATH = op.join(ROOT, "release")
PYREVIT_AIPFILE = op.join(RELEASE_PATH, "pyrevit.aip")
PYREVIT_CLI_AIPFILE = op.join(RELEASE_PATH, "pyrevit-cli.aip")
PYREVIT_VERSION_FILE = op.join(ROOT, "pyrevitlib/pyrevit/version")

# data files
PYREVIT_HOSTS_DATAFILE = op.join(BINPATH, "pyrevit-hosts.json")
PYREVIT_PRODUCTS_DATAFILE = op.join(BINPATH, "pyrevit-products.json")

# files containing version definition
VERSION_FILES = [
    op.join(DEVPATH, "pyRevit/AssemblyVersion.cs"),
    PYREVIT_VERSION_FILE,
]

# files containing copyright notice
COPYRIGHT_FILES = [
    op.join(DEVPATH, "pyRevit/AssemblyCopyright.cs"),
    op.join(ROOT, "pyrevitlib/pyrevit/versionmgr/about.py"),
    op.join(DOCS_DIR, "conf.py"),
]

# all source file locations that are part of pyRevit project
SOURCE_DIRS = [
    op.join(ROOT, "pyrevitlib/pyrevit"),
    DEVPATH,
]

# all extensions
EXTENSIONS_PATH = op.join(ROOT, "extensions")
