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
    return op.dirname(path)

def get_install_dir():
    return get_parent_directory( get_parent_directory( get_parent_directory(__file__)))

def get_pyrevit_clone_dir():
    return op.join(get_install_dir(), 'pyRevit')

def get_loader_clone_dir():
    return op.join(get_install_dir(), '__init__')

def get_git_dir():
    return op.join(get_install_dir(), '__git__\cmd')


installDir = get_install_dir()
pyrevitCloneDir = get_pyrevit_clone_dir()
loaderCloneDir = get_loader_clone_dir()
gitDir = get_git_dir()

print('Installation directory is: {0}'.format(installDir))
print('    pyRevit is cloned to: {0}'.format(pyrevitCloneDir))
print('    pyRevit loader is cloned to: {0}'.format(loaderCloneDir))
print('    git package is located at: {0}'.format(gitDir))

if op.exists('{0}\git.exe'.format(gitDir)):
    print('\nUPDATING PYTHON LOADER '.ljust(100,'-'))
    output = sp.Popen(r'{0}\git.exe fetch --all'.format(gitDir), \
                      stdout=sp.PIPE, stderr=sp.PIPE, cwd=loaderCloneDir, shell=True)
    print(output.communicate()[0])
    r1 = output.returncode
    
    output = sp.Popen(r'{0}\git.exe reset --hard'.format(gitDir), \
                      stdout=sp.PIPE, stderr=sp.PIPE, cwd=loaderCloneDir, shell=True)
    print(output.communicate()[0])
    r2 = output.returncode
    if r1 == r2 == 0:
        rr1 = True
        print('pyRevit loader successfully updated...')

    print('\nUPDATING PYTHON SCRIPT LIBRARY '.ljust(100,'-'))
    output = sp.Popen(r'{0}\git.exe fetch --all'.format(gitDir), \
                      stdout=sp.PIPE, stderr=sp.PIPE, cwd=loaderCloneDir, shell=True)
    print(output.communicate()[0])
    r1 = output.returncode
    
    output = sp.Popen(r'{0}\git.exe reset --hard'.format(gitDir), \
                      stdout=sp.PIPE, stderr=sp.PIPE, cwd=loaderCloneDir, shell=True)
    print(output.communicate()[0])
    r2 = output.returncode
    if r1 == r2 == 0:
        rr2 = True
        print('pyRevit scripts successfully updated...')
        
    if rr1 == rr2 == True:
        print('\n\npyRevit successfully updated...')
else:
    print('Can not find portable git package.')
