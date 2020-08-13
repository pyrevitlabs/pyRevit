"""Set various metadata properties across source files"""
from typing import Dict
import re
import datetime

from scripts import configs


def set_year(_: Dict[str, str]):
    """Update copyright notice"""
    this_year = datetime.datetime.today().year
    cp_finder = re.compile(r'© 2014-\d{4}')
    new_copyright = f'© 2014-{this_year}'
    print(f'Updating copyright notice to "{new_copyright}"...')
    for copyright_file in configs.COPYRIGHT_FILES:
        contents = []
        with open(copyright_file, 'r') as sfile:
            for cline in sfile.readlines():
                cline = cp_finder.sub(new_copyright, cline)
                contents.append(cline)
        with open(copyright_file, 'w') as sfile:
            sfile.writelines(contents)


def set_ver(args: Dict[str, str]):
    """Update version number"""
    ver_finder = re.compile(r'4\.\d\.\d')
    new_version = args["<ver>"]
    print(f'Updating version to v{new_version}...')
    for version_file in configs.VERSION_FILES:
        contents = []
        with open(version_file, 'r') as vfile:
            for cline in vfile.readlines():
                cline = ver_finder.sub(new_version, cline)
                contents.append(cline)
        with open(version_file, 'w') as vfile:
            vfile.writelines(contents)
