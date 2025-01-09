# -*- coding: UTF-8 -*-

from os.path import dirname, abspath, join
from pyrevit import script
from pyrevit.forms import alert, pick_file, pick_folder
from csv import reader

script.get_output().close_others()

config = script.get_config()

current_folder = dirname(abspath(__file__))
config.set_option(op_name='current_folder', value=current_folder)

critical_warnings_filepath = pick_file(init_dir=current_folder,
                                             file_ext="csv",
                                             multi_file=False, 
                                             title="Select the CSV file containing the critical warnings GUIDs")
if critical_warnings_filepath is None:
    script.exit()

with open(critical_warnings_filepath, 'r') as f:
    critical_warnings = []
    for line in reader(f):
        critical_warnings.append(line[0])
    config.set_option(op_name='critical_warnings', value=critical_warnings)

export_file_path = pick_folder(title="Where to save the data that will be collected?")
if export_file_path is None:
    script.exit()
config.set_option(op_name='export_file_path', value=join(export_file_path, 'projects_data.csv'))

script.save_config()
