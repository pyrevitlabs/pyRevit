#! bin/python
# tasks
# X docs
# - labs + cli
# - engines: ironpython loader and runners
# - engines: cpython
# - telemetry server, and autocomplete
    # echo "prepare git for go packages..."
    # git config --global http.https://pkg.re.followRedirects true
    # echo "formatting autocomplete helper code"
    # go fmt $AUTOCOMP
    # go get "github.com/lib/pq"
    # go get "gopkg.in/mgo.v2"
    # go get "github.com/denisenkom/go-mssqldb"
    # go get "github.com/go-sql-driver/mysql"
    # go get "github.com/mattn/go-sqlite3"
    # go get "github.com/gorilla/mux"
    # go get "github.com/satori/go.uuid"
    # go get "github.com/gofrs/uuid"
    # go get "pkg.re/essentialkaos/ek.v10/fmtc"
    # go get "github.com/asaskevich/govalidator"
    # go get "github.com/posener/complete"
# - installer: pyrevit (and update pyrevit_products.json)
# - installer: pyrevit cli (and update pyrevit_products.json)
    # echo "setting version "$PYREVIT_VERSION" on "$PYREVIT_AIPFILE
    # advancedinstaller.com "//edit" $PYREVIT_AIPFILE "//SetVersion" $PYREVIT_VERSION
    # AIPVersion=$(advancedinstaller.com "//edit" $PYREVIT_AIPFILE "//GetProperty" "ProductVersion")
    # echo $AIPVersion > $PYREVIT_VERSION_FILE
    # advancedinstaller.com "//build" $PYREVIT_AIPFILE
# utils:
# - add new revit version
# X collect changes
# - run tests?
# - start telemetry server for testing (mongo db docker)
# - push translation files into pyRevit (airtable api)

# TODO: primary goals
# - make my life easier building a new release of pyRevit
# - build docs for quick testing of doc build errors
# pylint: disable=broad-except,invalid-name
"""Utility to support pyRevit build and release workflows

Usage:
    {command_templates}

Commands:
    {command_helps}

Options:
    -h, --help                  Show this help


\033[1mREADME\033[0m

    Install these tools before starting the build process
        msbuild                 https://visualstudio.microsoft.com/vs/
        python 2.7 (docs)       https://www.python.org/downloads/
        pipenv (venv)           https://pipenv.readthedocs.io/en/latest/
        Advanced Installer (installer builder)
                                https://www.advancedinstaller.com
"""
import sys
import os
import os.path as op
import shutil
from typing import Dict
from collections import namedtuple

# pipenv dependencies
from docopt import docopt

# dev scripts
from scripts import utils
from scripts import configs

# cli info
__binname__ = os.environ["PYREVIT_BIN"] or op.splitext(op.basename(__file__))[0]
__version__ = "1.0"


class Command:
    """CLI command type"""

    def __init__(self, name, target, args, run):
        self.name = name
        self.target = target
        self.args = args
        self.help = run.__doc__
        self.template = " ".join(
            [x for x in [self.name, self.target, " ".join(self.args)] if x]
        )
        self.run = run


Change = namedtuple("Change", ["hash", "message"])


def install(args: Dict[str, str]):
    """Prepare build environment"""
    print("running install")


def report_changes_since(args: Dict[str, str]):
    """List commit messages from given tag to HEAD"""
    tag_hash = utils.system(["git", "rev-parse", f"{args['<tag>']}"])
    changes = []
    for cline in utils.system(["git", "log", "--oneline", f"{tag_hash}..HEAD"]).split(
        "\n"
    ):
        chash, cmsg = cline.split(" ", 1)
        changes.append(Change(hash=chash, message=cmsg))

    print("\n".join([x.message for x in changes]))


def build_docs(args: Dict[str, str]):  # pylint: disable=unused-argument
    """Build the python docs"""
    report = utils.system(
        ["pipenv", "run", "sphinx-build", "-b", "html", ".", configs.DOCS_BUILD],
        cwd="../docs",
    )
    print(report)


def open_docs(args: Dict[str, str]):  # pylint: disable=unused-argument
    """Open the local python docs in browser"""
    if op.exists(configs.DOCS_INDEX):
        if sys.platform == "darwin":
            runargs = ["open", configs.DOCS_INDEX]
        else:
            runargs = ["start", configs.DOCS_INDEX]
        utils.system(runargs)
    else:
        raise Exception("Docs are not built yet")


def clean_docs(args: Dict[str, str]):  # pylint: disable=unused-argument
    """Clean the local python docs build folder"""
    shutil.rmtree(configs.DOCS_BUILD)
    print("Removed docs build directory")


COMMANDS = [
    Command(name="install", target="", args=[], run=install),
    Command(name="changelog", target="", args=["<tag>"], run=report_changes_since),
    Command(name="build", target="docs", args=[], run=build_docs),
    Command(name="open", target="docs", args=[], run=open_docs),
    Command(name="clean", target="docs", args=[], run=clean_docs),
]


def run_command(args: Dict[str, str]):
    """Process cli args and run the appropriate commands"""
    for cmd in COMMANDS:
        if args[cmd.name]:
            cmd.run(args)


if __name__ == "__main__":
    try:
        # run the appropriate command
        run_command(
            # process args
            docopt(
                __doc__.format(
                    command_templates="\n    ".join(
                        [f"{__binname__} {x.template}" for x in COMMANDS]
                    ),
                    command_helps="\n    ".join(
                        [f"{x.template:27} {x.help}" for x in COMMANDS]
                    ),
                ),
                version="{} {}".format(__binname__, __version__),
            )
        )
    # gracefully handle exceptions and print results
    except Exception as run_ex:
        sys.stderr.write("[ERROR] %s\n" % str(run_ex))
        sys.exit(1)
