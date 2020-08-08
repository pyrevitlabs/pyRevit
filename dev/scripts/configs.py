"""Dev scripts configs"""
import os.path as op

# ==============================================================================
# Configs
# ------------------------------------------------------------------------------
DOCS_DIR = "../docs/"
DOCS_BUILD = DOCS_DIR + "_build/"
DOCS_INDEX = DOCS_BUILD + "index.html"

BINPATH = "../bin/"

LABS = "./pyRevitLabs/pyRevitLabs.sln"

# API file paths must be absolute otherwise advancedinstaller will mess up
# the relative source paths defined inside the api file and fails
PYREVIT_AIPFILE = op.abspath("../../release/pyrevit.aip")
PYREVIT_CLI_AIPFILE = op.abspath("../../release/pyrevit-cli.aip")
PYREVIT_VERSION = ""
PYREVIT_VERSION_FILE = "../pyrevitlib/pyrevit/version"
PYREVIT_CLI_VERSION = ""

USAGEPATTERNS = "./pyRevitLabs/pyRevitCLI/Resources/UsagePatterns.txt"
AUTOCOMP = "pyrevit-autocomplete.go"
AUTOCOMPBIN = BINPATH + "pyrevit-autocomplete.exe"

TELEMETRYSERVERPATH = "./pyRevitTelemetryServer/"
TELEMETRYSERVER = TELEMETRYSERVERPATH + "main.go"
TELEMETRYSERVERBIN = BINPATH + "pyrevit-telemetryserver.exe"
