"""
Copyright (c) 2014-2017 Ehsan Iran-Nejad
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

__doc__ = 'Shows the preferences window for pyrevit. You can customize how pyrevit loads and set some basic ' \
          'parameters here.'

__title__ = 'Sample\nCommand'


import scriptutils as su

su.logger.critical('Test Log Level')
su.logger.warning('Test Log Level')
su.logger.info('Test Log Level :ok_hand_sign:')
su.logger.debug('Test Log Level')

print('\n\n')

print('-'*100)
print('script info')
print('-'*100)
print type(su.my_info)
print su.my_info
print su.my_info.name
print su.my_info.ui_title
print su.my_info.unique_name
print su.my_info.unique_avail_name
print su.my_info.doc_string
print su.my_info.author
print su.my_info.cmd_options
print su.my_info.cmd_context
print su.my_info.min_pyrevit_ver
print su.my_info.min_revit_ver
print su.my_info.cmd_options
print su.my_info.script_file
print su.my_info.config_script_file
print su.my_info.icon_file
print su.my_info.library_path
print su.my_info.syspath_search_paths

print('-'*100)
print('script config')
print('-'*100)

print type(su.my_config)
print su.my_config

print('-'*100)
print('script temp and data files')
print('-'*100)
print su.my_temp_file
print su.my_data_file
