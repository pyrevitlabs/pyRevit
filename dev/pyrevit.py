"""Utility to support pyRevit build and release workflows

\033[1mUsage:\033[0m
    {command_templates}

\033[1mCommands:\033[0m
    {command_helps}

\033[1mOptions:\033[0m
    -h, --help                  Show this help

\033[1m  * Requirements:\033[0m
    Install these tools before starting the build process
        msbuild                 visualstudio.microsoft.com/downloads/
                                ensure `msbuild` is in %PATH%
        signtool                for digitally signing binaries
        python 2 (docs)         www.python.org/downloads/
        python 3 (build)        www.python.org/downloads/
        pipenv (venv)           pipenv.readthedocs.io/en/latest/
        Advanced Installer (installer builder)
                                www.advancedinstaller.com
        mingw (gcc)             http://mingw.org
                                ensure `gcc` is in %PATH%
"""
# todo
# - [ ] add new supported revit version
# - [ ] run tests?
# - [ ] start telemetry server for testing (mongo db docker)
# - [ ] push translation files into pyRevit (airtable api)

# pylint: disable=invalid-name,broad-except
import logging
import sys
import os.path as op

# pipenv dependencies
from docopt import docopt

# dev scripts
from scripts import utils
from scripts.utils import Command

# functions
import _install as install
import _apidocspy as apidocspy
import _autocomplete as autocomplete
import _changelog as changelog
import _build as build
import _buildall as buildall
import _release as release
import _setprop as setprop
import _misc as misc


# cli info
__binname__ = op.splitext(op.basename(__file__))[0]
__version__ = "1.0"


logging.basicConfig()
logger = logging.getLogger()
# logger.setLevel(logging.DEBUG)


COMMANDS = [
    Command(name="install", target="", args=[], run=install.install),
    Command(
        name="changelog",
        target="",
        args=["<tag>"],
        run=changelog.report_changes_since,
    ),
    Command(name="build", target="docs", args=[], run=apidocspy.build_docs),
    Command(name="open", target="docs", args=[], run=apidocspy.open_docs),
    Command(name="clean", target="docs", args=[], run=apidocspy.clean_docs),
    Command(name="build", target="all", args=[], run=buildall.build_all),
    Command(name="build", target="clean", args=[], run=buildall.build_clean),
    Command(name="build", target="labs", args=[], run=build.build_labs),
    Command(name="build", target="engines", args=[], run=build.build_engines),
    Command(
        name="build",
        target="autocomplete",
        args=[],
        run=autocomplete.build_autocomplete,
    ),
    Command(
        name="build", target="telemetry", args=[], run=build.build_telemetry
    ),
    Command(
        name="release", target="", args=["<tag>"], run=release.create_release
    ),
    Command(
        name="set", target="copyright", args=[], run=setprop.update_copyright
    ),
    Command(
        name="set",
        target="version",
        args=["<version>"],
        run=setprop.update_versions,
    ),
    Command(
        name="report",
        target="sloc",
        args=[],
        run=misc.count_sloc,
    ),
    Command(
        name="report",
        target="downloads",
        args=[],
        run=misc.report_downloads,
    ),
]


def format_cmd_help(helpstring):
    """Format command help for cli help"""
    formatted_help = helpstring
    helplines = helpstring.split("\n")
    helplines = [x.strip() for x in helplines]
    if helplines:
        formatted_help = helplines[0]
        for hline in helplines[1:]:
            if hline:
                formatted_help += f"\n{'':33}{hline}"
    return formatted_help


def prepare_docopt_help():
    """Prepare docstring for docopt"""
    return __doc__.format(
        command_templates="\n    ".join(
            [f"{__binname__} {x.template}" for x in COMMANDS]
        ),
        command_helps="\n    ".join(
            [f"{x.template:27} {format_cmd_help(x.help)}" for x in COMMANDS]
        ),
    )


if __name__ == "__main__":
    try:
        # run the appropriate command
        utils.run_command(
            COMMANDS,
            # process args
            docopt(
                doc=prepare_docopt_help(),
                version="{} {}".format(__binname__, __version__),
            ),
        )
    # gracefully handle exceptions and print results
    except Exception as run_ex:
        logger.error("%s", str(run_ex))
        sys.exit(1)
