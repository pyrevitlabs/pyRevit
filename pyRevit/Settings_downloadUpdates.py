"""
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE
"""

__doc__ = 'Downloads updates from the github repository. This function works only when pyRevit was ' \
          'installed using the setup package provided on the github repo. ' \
          '(It needs the portable git tool to download the updates)'


import os.path as op
import subprocess as sp


def get_parent_directory(path):
    return op.split(op.dirname(path))[0]


cloneDir = get_parent_directory(__file__)
gitDir = op.dirname(cloneDir)

print('Parent directory is: {0}'.format(cloneDir))
print('git package is located at: {0}'.format(gitDir))
print('\nUpdating pyRevit from github repository...')
if op.exists('{0}\git\cmd\git.exe'.format(gitDir)):
    output = sp.Popen(r'{0}\git\cmd\git.exe fetch --all'.format(gitDir), stdout=sp.PIPE, stderr=sp.PIPE, cwd=cloneDir,
                      shell=True)
    print(output.communicate()[0])
    r1 = output.returncode
    output = sp.Popen(r'{0}\git\cmd\git.exe reset --hard origin/master'.format(gitDir), stdout=sp.PIPE, stderr=sp.PIPE,
                      cwd=cloneDir, shell=True)
    print(output.communicate()[0])
    r2 = output.returncode
    if r1 == r2 == 0:
        print('pyRevit successfully updated...You can close this window now.')
else:
    print('Can not find portable git package.')
