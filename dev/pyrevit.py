"""Utility to support pyRevit build and release workflows

<b>Usage:</b>
    {command_templates}

<b>  * Requirements:</b>
    Install these tools before starting the build process. Add the binary
    directory for these tools to your system PATH. Run `check` to test

    dotnet SDK              for building labs (https://dotnet.microsoft.com/download/dotnet)
    Visual Studio:          for building labs (https://visualstudio.microsoft.com/downloads/)
    └── msbuild                 building msi installers using Wix Tools
    └── certutil                managing signing certificate
    └── signtool                digitally signing binaries
    gcc                     for building sqlite package in telemetry server (http://mingw.org)
    go                      for building telemetry server (https://golang.org)
    Inno Setup Compiler     for buidling installers (https://jrsoftware.org/isinfo.php)
    └── iscc                    buidling installers from scripts
    choco                   for building and publishing choco packages (https://chocolatey.org)
    nuget                   for signing choco nuget package (https://www.nuget.org/downloads)
    Wix Tools               for building MSI installers (https://wixtoolset.org/releases/)
    pipenv                  for managing python virtual envs (https://pipenv.readthedocs.io/)
    python 3                for the build tools (https://www.python.org/downloads/)
    pygount                 for counting code lines (https://pypi.org/project/pygount/)
    git                     for creating release reports (https://git-scm.com)
    docker                  for telemetry server tests (https://www.docker.com/products/docker-desktop)

    Some of the commands call web APIs for necessary information.
    Access tokens must be set in env vars otherwise access will be
    limited to API rate limits:

    GITHUB_TOKEN            for accessing repo info on github
    AIRTABLE_TOKEN          for accessing shared tables on airtable

    Sign commands require certificate information on a series of
    env vars otherwise signing process will fail:

    CERTIFICATENAME         certificate name
    CERTIFICATESHA1         certificate fingerprint
    CERTIFICATE             certificate *.pfx contents in base64
    CERTIFICATEPASSWORD     certificate password

"""  # pylint: disable=line-too-long
# - [ ] run tests?
# - [ ] optional arguments

# pylint: disable=invalid-name,broad-except
import logging
import sys
import os.path as op
from typing import Dict

# pipenv dependencies
from docopt import docopt

# dev scripts
from scripts import utils
from scripts.utils import Command

# functions
import _install as install
# import _apidocspy as apidocspy # not used by new documentation workflow
import _autocomplete as autoc
import _labs as labs
import _build as build
import _changelog as clog
import _hostdata as hostdata
import _release as release
import _props as props
import _telem as telem
import _misc as misc


# cli info
__binname__ = op.splitext(op.basename(__file__))[0]


logging.basicConfig()
logger = logging.getLogger()


def prepare_docopt_help(for_print=False):
    """Prepare docstring for docopt"""
    command_templates = ""
    if for_print:
        command_templates = "\n    ".join(
            [
                f"{__binname__} {x.template:30} {utils.format_help(x.help)}"
                for x in COMMANDS
            ]
        )
    else:
        command_templates = "\n    ".join(
            [f"{__binname__} {x.template}" for x in COMMANDS]
        )

    return utils.colorize(__doc__.format(command_templates=command_templates))


def print_help(_: Dict[str, str]):
    """Print this help"""
    print(prepare_docopt_help(for_print=True))
    sys.exit()


COMMANDS = [
    # release
    Command(name="release", target="", args=["<tag>"], run=release.create_release),
    # notify issue threads
    Command(name="notify", target="", args=["<build>", "<url>", "[<tag>]"], run=clog.notify_issues),
    # signning builds
    Command(name="sign", target="addcert", args=[], run=release.setup_certificate),
    Command(name="sign", target="products", args=[], run=release.sign_binaries),
    Command(name="sign", target="installers", args=[], run=release.sign_installers),
    # build
    Command(name="build", target="products", args=[], run=build.build_binaries),
    Command(name="build", target="labs", args=[], run=labs.build_labs),
    Command(name="build", target="engines", args=[], run=labs.build_engines),
    Command(name="build", target="autocmp", args=[], run=autoc.build_autocmp),
    Command(name="build", target="telem", args=[], run=telem.build_telem),
    Command(name="build", target="installers", args=[], run=release.build_installers),
    Command(name="build", target="commit", args=[], run=release.commit_and_tag_build),
    Command(name="clean", target="labs", args=[], run=build.clean_build),
    # unit testing
    Command(name="test", target="telem", args=[], run=telem.start_telem),
    # manual data setters
    Command(name="set", target="year", args=[], run=props.set_year),
    Command(name="set", target="version", args=["<ver>"], run=props.set_ver),
    Command(name="set", target="next-version", args=[], run=props.set_next_ver),
    Command(name="set", target="build", args=["<build>"], run=props.set_build_ver),
    Command(name="set", target="products", args=[], run=release.set_product_data),
    Command(name="set", target="locales", args=[], run=props.set_locales),
    # reports
    Command(name="report", target="sloc", args=[], run=misc.count_sloc),
    Command(name="report", target="downloads", args=[], run=misc.report_dls),
    Command(name="report", target="changelog", args=["[<tag>]"], run=clog.report_changelog),
    Command(name="report", target="releasenotes", args=[], run=clog.generate_release_notes),
    # misc
    Command(name="add", target="host", args=[], run=hostdata.add_hostdata),
    Command(name="help", target="", args=[], run=print_help),
    # prepare and verify build env
    Command(name="install", target="", args=[], run=install.install),
    Command(name="check", target="", args=[], run=install.check),
]


if __name__ == "__main__":
    if "--debug" in sys.argv:
        logger.setLevel(logging.DEBUG)
        sys.argv.remove("--debug")

    try:
        # process args
        args = docopt(
            doc=prepare_docopt_help(),
            version="{} {}".format(__binname__, props.get_version()),
            help=False,
        )
        # run the appropriate command
        utils.run_command(COMMANDS, args)
    # gracefully handle exceptions and print results
    except Exception as run_ex:
        logger.error("%s", str(run_ex))
        sys.exit(1)
