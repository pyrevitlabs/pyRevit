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
import sys
import subprocess
from collections import namedtuple


Change = namedtuple('Change', ['hash', 'message'])


def system(args):
    """Run a command and return the stdout"""
    res = subprocess.run(args, capture_output=True, check=True)
    return res.stdout.decode().strip()

def report_changes_since(tag):
    """List commit messages between given tag and HEAD"""
    tag_hash = system(["git", "rev-parse", f"{tag}"])
    changes = []
    for cline in system(
            ["git", "log", "--oneline", f"{tag_hash}..HEAD"]).split('\n'):
        chash, cmsg = cline.split(' ', 1)
        changes.append(Change(hash=chash, message=cmsg))
    return changes


changes_since = report_changes_since(sys.argv[1])
print('\n'.join([x.message for x in changes_since]))
