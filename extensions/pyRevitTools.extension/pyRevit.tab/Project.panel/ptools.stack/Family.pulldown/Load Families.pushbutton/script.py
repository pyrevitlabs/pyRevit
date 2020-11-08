"""This tool gives you the option to load multiple Families from a folder and its subfolders.
You can choose to load the Family with all its Types, or select Types for each Family.
"""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import os
from pyrevit import forms
from pyrevit import script

# Custom modules in lib/
from file_utils import FileFinder
from family_utils import FamilyLoader

logger = script.get_logger()
output = script.get_output()


# Get directory with families
directory = forms.pick_folder("Select parent folder of families")
logger.debug('Selected parent folder: {}'.format(directory))
if directory is None:
    logger.debug('No directory selected. Calling script.exit')
    script.exit()

# Find family files in directory
finder = FileFinder(directory)
finder.search('*.rfa')

# Excluding backup files
backup_pattern = r'^.*\.\d{4}\.rfa$'
finder.exclude_by_pattern(backup_pattern)
paths = finder.paths

# Dictionary to look up absolute paths by relative paths
path_dict = dict()
for path in paths:
    path_dict.update({os.path.relpath(path, directory): path})

# User input -> Select families from directory
family_select_options = sorted(
    path_dict.keys(),
    key=lambda x: (x.count(os.sep), x))  # Sort by nesting level
selected_families = forms.SelectFromList.show(
    family_select_options,
    title="Select Families",
    width=500,
    button_name="Load Families",
    multiselect=True)
if selected_families is None:
    logger.debug('No families selected. Calling script.exit()')
    script.exit()
logger.debug('Selected Families: {}'.format(selected_families))

# Dictionary to look up FamilyLoader method by selected option
family_loading_options = {
    "Load All Types Per Family": "load_all",
    "Ask Which Types To Load Per Family": "load_selective"}
selected_loading_option = forms.CommandSwitchWindow.show(
    family_loading_options.keys(),
    message='Select loading option:',)
if selected_loading_option is None:
    logger.debug('No loading option selected. Calling script.exit()')
    script.exit()

# User input -> Select loading option (load all, load certain symbols)
logger.debug('Selected loading option: {}'.format(selected_loading_option))
laoding_option = family_loading_options[selected_loading_option]


# Feedback on already loaded families
already_loaded = set()

# Loading selected families
max_value = len(selected_families)
with forms.ProgressBar(title='Loading Family {value} of {max_value}',
                       cancellable=True) as pb:
    for count, family_path in enumerate(selected_families, 1):
        if pb.cancelled:
            break
        pb.update_progress(count, max_value)

        family = FamilyLoader(path_dict[family_path])
        logger.debug('Loading family: {}'.format(family.name))
        loaded = family.is_loaded
        if loaded:
            logger.debug('Family is already loaded: {}'.format(family.path))
            already_loaded.add(family)
            continue
        getattr(family, laoding_option)()

# Feedback on already loaded families
if len(already_loaded) != 0:
    output.print_md('### Families that were already loaded:')
    for family in sorted(already_loaded):
        print(family.path)
