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

__doc__ = 'Downloads updates from the github repository. This function works only when pyrevit was ' \
          'installed using the setup package provided on the github repo. ' \
          '(It needs the portable git tool to download the updates)'


from pyrevit.loader import updater

updater.update_pyrevit()

# import os.path as op
# import subprocess as sp
# import re

# from Autodesk.Revit.UI import TaskDialog


# class ErrorFindingBranch(Exception):
    # pass


# def get_parent_directory(path):
    # return op.dirname(path)


# def get_install_dir():
    # return get_parent_directory(get_parent_directory(get_parent_directory(__file__)))


# def get_pyrevit_clone_dir():
    # return op.join(get_install_dir(), 'pyrevit')


# def get_loader_clone_dir():
    # return op.join(get_install_dir(), '__init__')


# def get_git_dir():
    # return op.join(get_install_dir(), '__git__', 'cmd')


# def git_get_current_branch(cloneDir):
    # global git_executive
    # bfinder = re.compile('\*\s(.+)')
    # output = sp.Popen(r'{0} branch'.format(git_executive), \
                      # stdout=sp.PIPE, stderr=sp.PIPE, cwd=cloneDir, shell=True)
    # res = bfinder.findall(output.communicate()[0])
    # if len(res) > 0:
        # print('Current branch is {}'.format(res[0]))
        # return res[0]
    # else:
        # raise ErrorFindingBranch()


# def git_pull_overwrite(cloneDir):
    # global git_executive
    # report = ''
    # r1 = r2 = False

    # # Fetch changes
    # output = sp.Popen(r'{0} fetch --all'.format(git_executive), \
                      # stdout=sp.PIPE, stderr=sp.PIPE, cwd=cloneDir, shell=True)
    # print(output.communicate()[0])
    # # print(output.returncode)
    # r1 = output.returncode

    # # Hard reset current branch to origin/branch
    # try:
        # output = sp.Popen(r'{0} reset --hard origin/{1}'.format(git_executive, git_get_current_branch(cloneDir)), \
                          # stdout=sp.PIPE, stderr=sp.PIPE, cwd=cloneDir, shell=True)
        # print(output.communicate()[0])
        # # print(output.returncode)
        # r2 = output.returncode
    # except ErrorFindingBranch as err:
        # print('Error finding current git branch...Skipping update...')
        # raise err

    # if (r1 == r2 == 0):
        # print('Successfully updated repository...')
    # else:
        # print('Error in updating repository...')


# installDir = get_install_dir()
# pyrevitCloneDir = get_pyrevit_clone_dir()
# loaderCloneDir = get_loader_clone_dir()
# gitDir = get_git_dir()
# git_executive = '\"' + op.join(gitDir, 'git.exe') + '\"'

# print('Installation directory is: {0}'.format(installDir))
# print('Portable git package is located at: {0}'.format(gitDir))

# if op.exists('{0}\git.exe'.format(gitDir)):
    # try:
        # print('\nUPDATING PYTHON LOADER '.ljust(100, '-'))
        # print('pyrevit loader has been cloned to: {0}\n'.format(loaderCloneDir))
        # git_pull_overwrite(loaderCloneDir)
    # except:
        # print('Error Updating loader repository...The cloned repo might be corrupt or no internet access.\n'      \
              # 'Trying to update the main repository now')
    # try:
        # print('\n\nUPDATING PYTHON SCRIPT LIBRARY '.ljust(100, '-'))
        # print('pyrevit has been cloned to: {0}\n'.format(pyrevitCloneDir))
        # git_pull_overwrite(pyrevitCloneDir)

        # TaskDialog.Show('pyrevit', 'Update completed. reload pyrevit now to see changes...')
        # __window__.Focus()
    # except:
        # TaskDialog.Show('pyrevit', 'Error Updating repository...Please check your internet connection. ' \
                                   # 'If the updater still did not work please copy the printed report and ' \
                                   # 'contact the developers...')
        # __window__.Focus()
# else:
    # print('Can not find portable git package.')
