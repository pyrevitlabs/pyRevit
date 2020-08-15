"""Set various metadata properties across source files"""
import sys
from typing import Dict
import re
import datetime

from scripts import configs
from scripts import utils


def _modify_contents(files, finder, new_value):
    for text_file in files:
        contents = []
        file_changed = False
        with open(text_file, "r") as sfile:
            for cline in sfile.readlines():
                newcline = finder.sub(new_value, cline)
                if cline != newcline:
                    file_changed = True
                contents.append(newcline)
        if file_changed:
            with open(text_file, "w") as sfile:
                sfile.writelines(contents)


def get_version():
    """Get current version"""
    ver_finder = re.compile(r"4\.\d\.\d")
    for verfile in configs.VERSION_FILES:
        with open(verfile, 'r') as vfile:
            for cline in vfile.readlines():
                if match := ver_finder.search(cline):
                    return match.group()


def set_year(_: Dict[str, str]):
    """Update copyright notice"""
    this_year = datetime.datetime.today().year
    cp_finder = re.compile(r"© 2014-\d{4}")
    new_copyright = f"© 2014-{this_year}"
    print(f'Updating copyright notice to "{new_copyright}"...')
    _modify_contents(
        files=configs.COPYRIGHT_FILES, finder=cp_finder, new_value=new_copyright
    )


def set_ver(args: Dict[str, str]):
    """Update version number"""
    ver_finder = re.compile(r"4\.\d\.\d")
    new_version = args["<ver>"]
    if ver_finder.match(new_version):
        print(f"Updating version to v{new_version}...")
        _modify_contents(
            files=configs.VERSION_FILES,
            finder=ver_finder,
            new_value=new_version,
        )
    else:
        print(utils.colorize(
            "<red>Invalid version format (e.g. 4.8.0)</red>"
        ))
        sys.exit(1)
