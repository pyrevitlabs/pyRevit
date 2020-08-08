# tasks
# - docs
# - labs + cli
# - engines: ironpython loader and runners
# - engines: cpython
# - telemetry server, and autocomplete
# - installer: pyrevit (and update pyrevit_products.json)
# - installer: pyrevit cli (and update pyrevit_products.json)
# utils:
# - add new revit version
# X collect changes
# - run tests?
# - start telemetry server for testing (mongo db docker)
# - push translation files into pyRevit (airtable api)

# TODO: primary goals
# - make my life easier building a new release of pyRevit
# - build docs for quick testing of doc build errors
#pylint: disable=broad-except,invalid-name
"""Utility to support pyRevit build and release workflows

Usage:
    {cliname} changelog <tag>
    {cliname} build docs

Commands:
    changelog <tag>        List commit messages from given tag to HEAD
    build docs             Build the python docs

Options:
    -h, --help             Show this help
"""
import sys
import os.path as op
from typing import List, Optional
import subprocess
from collections import namedtuple

# pipenv dependencies
from docopt import docopt

# cli info
__binname__ = op.splitext(op.basename(__file__))[0] # grab script name
__version__ = '1.0'


Change = namedtuple('Change', ['hash', 'message'])


class CLIArgs:
    """Data type to hold command line args"""
    def __init__(self, args):
        if args['changelog']:
            self.command = 'changelog'
            self.tag = args['<tag>']
        elif args['build']:
            self.command = 'build'
            self.target = 'docs'


def system(args: List[str], cwd: Optional[str] = None):
    """Run a command and return the stdout"""
    res = subprocess.run(args, capture_output=True, check=True, cwd=cwd)
    return res.stdout.decode().strip()


def report_changes_since(cfg: CLIArgs):
    """List commit messages between given tag and HEAD"""
    tag_hash = system(["git", "rev-parse", f"{cfg.tag}"])
    changes = []
    for cline in system(
            ["git", "log", "--oneline", f"{tag_hash}..HEAD"]).split('\n'):
        chash, cmsg = cline.split(' ', 1)
        changes.append(Change(hash=chash, message=cmsg))
    return changes


def build_docs(cfg: CLIArgs):
    """Build python documentation"""
    report = system(
        ["pipenv", "run", "sphinx-build", "-b", "html", ".", "./_build"],
        cwd='../docs'
        )
    print(report)


def run_command(cfg: CLIArgs):
    """Process cli args and run the appropriate commands"""
    if cfg.command == 'changelog':
        changes_since = report_changes_since(cfg)
        print('\n'.join([x.message for x in changes_since]))
    
    elif cfg.command == 'build':
        if cfg.target == 'docs':
            build_docs(cfg)


if __name__ == '__main__':
    try:
        # do the work
        run_command(
            # make settings from cli args
            cfg=CLIArgs(
                # process args
                docopt(
                    __doc__.format(cliname=__binname__),
                    version='{} {}'.format(__binname__, __version__)
                )
            )
        )
    # gracefully handle exceptions and print results
    except Exception as run_ex:
        sys.stderr.write("[ERROR] %s\n" % str(run_ex))
        sys.exit(1)
