"""Utility to support pyRevit build and release workflows

<b>Usage:</b>
    {command_templates}

<b>Commands:</b>
    {command_helps}

<b>Options:</b>
    -h, --help                  Show this help

<b>  * Requirements:</b>
    Install these tools before starting the build process
        msbuild                 visualstudio.microsoft.com/downloads/
                                ensure `msbuild` is in %PATH%
        mingw (gcc)             http://mingw.org
                                ensure `gcc` is in %PATH%
        signtool                for digitally signing binaries
        Advanced Installer (installer builder)
                                www.advancedinstaller.com
        pipenv (venv)           pipenv.readthedocs.io/en/latest/
        python 2 (docs)         www.python.org/downloads/
        python 3 (build)        www.python.org/downloads/
        docker                  for telemetry server tests
"""
# - [ ] run tests?
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
import _autocomplete as autoc
import _labs as labs
import _buildall as buildall
import _changelog as clog
import _hostdata as hostdata
import _release as release
import _setprop as setprop
import _telem as telem
import _misc as misc


# cli info
__binname__ = op.splitext(op.basename(__file__))[0]
__version__ = "1.0"


logging.basicConfig()
logger = logging.getLogger()
# logger.setLevel(logging.DEBUG)


COMMANDS = [
    # prepare and verify build env
    Command(name="install", target="", args=[], run=install.install),
    Command(name="check", target="", args=[], run=install.check),
    # main release command
    Command(
        name="release", target="", args=["<tag>"], run=release.create_release
    ),
    # individual release steps for testing
    Command(name="changelog", target="", args=["<tag>"], run=clog.report_clog),
    Command(name="build", target="all", args=[], run=buildall.build_all),
    Command(name="build", target="docs", args=[], run=apidocspy.build_docs),
    Command(name="open", target="docs", args=[], run=apidocspy.open_docs),
    Command(name="clean", target="docs", args=[], run=apidocspy.clean_docs),
    Command(name="build", target="labs", args=[], run=labs.build_labs),
    Command(name="clean", target="labs", args=[], run=buildall.build_clean),
    Command(name="build", target="engines", args=[], run=labs.build_engines),
    Command(name="build", target="autocmp", args=[], run=autoc.build_autocmp),
    Command(name="build", target="telem", args=[], run=telem.build_telem),
    # unit testing
    Command(name="test", target="telem", args=[], run=telem.start_telem),
    # manual data setters
    Command(name="update", target="year", args=[], run=setprop.set_year),
    Command(name="add", target="host", args=[], run=hostdata.add_hostdata),
    Command(name="set", target="version", args=["<ver>"], run=setprop.set_ver),
    # reports
    Command(name="report", target="sloc", args=[], run=misc.count_sloc,),
    Command(name="report", target="downloads", args=[], run=misc.report_dls),
]


def prepare_docopt_help():
    """Prepare docstring for docopt"""
    return utils.colorize(
        __doc__.format(
            command_templates="\n    ".join(
                [f"{__binname__} {x.template}" for x in COMMANDS]
            ),
            command_helps="\n    ".join(
                [
                    f"{x.template:27} {utils.format_cmd_help(x.help)}"
                    for x in COMMANDS
                ]
            ),
        )
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
