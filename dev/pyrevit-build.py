"""Utility to support pyRevit build and release workflows

\033[1mUsage:\033[0m
    {command_templates}

\033[1mCommands:\033[0m
    {command_helps}

\033[1mOptions:\033[0m
    -h, --help                  Show this help


\033[1mRequirements:\033[0m
    Install these tools before starting the build process
        msbuild                 visualstudio.microsoft.com/downloads/
        python 2 (docs)         www.python.org/downloads/
        python 3 (build)        www.python.org/downloads/
        pipenv (venv)           pipenv.readthedocs.io/en/latest/
        Advanced Installer (installer builder)
                                www.advancedinstaller.com
"""
# pylint: disable=invalid-name,broad-except
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
from scripts.utils import Command
from scripts import configs

# cli info
__binname__ = (
    os.environ.get("PYREVIT_BIN", None) or op.splitext(op.basename(__file__))[0]
)
__version__ = "1.0"


Change = namedtuple("Change", ["hash", "message"])


def install(_: Dict[str, str]):
    """Prepare build environment"""
    print("running install")


def report_changes_since(args: Dict[str, str]):
    """List commit messages from given tag to HEAD"""
    tag_hash = utils.system(["git", "rev-parse", f"{args['<tag>']}"])
    changes = []
    changelines = utils.system(["git", "log", "--oneline", f"{tag_hash}..HEAD"])
    for cline in changelines.split("\n"):
        chash, cmsg = cline.split(" ", 1)
        changes.append(Change(hash=chash, message=cmsg))

    print("\n".join([x.message for x in changes]))


def build_docs(_: Dict[str, str]):
    """Build the python docs"""
    report = utils.system(
        [
            "pipenv",
            "run",
            "sphinx-build",
            "-b",
            "html",
            configs.DOCS_DIR,
            configs.DOCS_BUILD,
        ],
        cwd=configs.DOCS_DIR
    )
    print(report)


def open_docs(_: Dict[str, str]):
    """Open the local python docs in browser"""
    if op.exists(configs.DOCS_INDEX):
        if sys.platform == "darwin":
            runargs = ["open", configs.DOCS_INDEX]
        else:
            runargs = ["start", configs.DOCS_INDEX]
        utils.system(runargs)
    else:
        raise Exception("Docs are not built yet")


def clean_docs(_: Dict[str, str]):
    """Clean the local python docs build folder"""
    shutil.rmtree(configs.DOCS_BUILD)
    print("Removed docs build directory")


def build_labs(_: Dict[str, str]):
    """Build pyRevit labs"""
    # clean
    utils.system(
        [f"msbuild {configs.LABS} ", "-t:Restore ", "-p:Configuration=Release"]
    )
    # build
    utils.system([f"msbuild {configs.LABS} ", "-t:Build ", "-p:Configuration=Release"])


def create_release(_: Dict[str, str]):
    """Create pyRevit release (build, test, publish)"""


COMMANDS = [
    Command(name="install", target="", args=[], run=install),
    Command(name="release", target="", args=["<tag>"], run=create_release),
    Command(name="changelog", target="", args=["<tag>"], run=report_changes_since),
    Command(name="build", target="docs", args=[], run=build_docs),
    Command(name="open", target="docs", args=[], run=open_docs),
    Command(name="clean", target="docs", args=[], run=clean_docs),
    Command(name="build", target="labs", args=[], run=build_labs),
]


if __name__ == "__main__":
    try:
        # run the appropriate command
        utils.run_command(
            COMMANDS,
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
            ),
        )
    # gracefully handle exceptions and print results
    except Exception as run_ex:
        sys.stderr.write("[ERROR] %s\n" % str(run_ex))
        sys.exit(1)
