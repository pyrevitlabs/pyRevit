"""Load multiple Families from a folder and its subfolders.

This tool gives you the option to load multiple Families from a folder and its subfolders.
You can choose to load the Family with all its Types, or select Types for each Family.
If some of the selected Families are already in the project, you are asked whether to
skip them or to overwrite them.
"""

# pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import os
from collections import namedtuple

from pyrevit import forms
from pyrevit import script

# Custom modules in lib/
from file_utils import FileFinder
from family_utils import FamilyLoader, get_family_name, get_loaded_family_names

logger = script.get_logger()
output = script.get_output()

BACKUP_PATTERN = r"^.*\.\d{4}\.rfa$"

LOADING_OPTIONS = {
    "Load All Types Per Family": "load_all",
    "Ask Which Types To Load Per Family": "load_selective",
}

SKIP_EXISTING = "Skip Them"
OVERWRITE_EXISTING = "Overwrite Them"

LoadOutcome = namedtuple("LoadOutcome", ["overwritten", "skipped", "failed"])


def collect_family_paths(directory):
    """Finds the family files under a directory, ignoring Revit backups.

    Args:
        directory (str): folder searched recursively for .rfa files

    Returns:
        dict[str, str]: path relative to directory, mapped to its absolute path
    """
    finder = FileFinder(directory)
    finder.search("*.rfa")
    finder.exclude_by_pattern(BACKUP_PATTERN)
    return {os.path.relpath(path, directory): path for path in finder.paths}


def ask_families(path_dict):
    """Asks which of the found families to load.

    Args:
        path_dict (dict[str, str]): relative to absolute family paths

    Returns:
        list[str] | None: selected absolute paths, None if the user cancelled
    """
    sorted_by_nesting_level = sorted(
        path_dict.keys(), key=lambda x: (x.count(os.sep), x)
    )
    selection = forms.SelectFromList.show(
        sorted_by_nesting_level,
        title="Select Families",
        width=500,
        button_name="Load Families",
        multiselect=True,
    )
    if not selection:
        return None
    logger.debug("Selected Families: {}".format(selection))
    return [path_dict[relative_path] for relative_path in selection]


def ask_overwrite(paths):
    """Asks what to do with the selected families that are already in the project.

    The question is skipped when the selection does not collide with the
    project, so a clean load stays a single prompt.

    Args:
        paths (list[str]): absolute paths of the family files to load

    Returns:
        bool | None: True to overwrite, False to skip,
            None if the user cancelled
    """
    loaded_names = get_loaded_family_names()
    existing = [path for path in paths if get_family_name(path) in loaded_names]
    if not existing:
        logger.debug("No selected family is already in the project.")
        return False

    selection = forms.CommandSwitchWindow.show(
        [SKIP_EXISTING, OVERWRITE_EXISTING],
        message="{} of {} selected Families are already in the project:".format(
            len(existing), len(paths)
        ),
    )
    logger.debug("Selected option for existing families: {}".format(selection))
    if selection is None:
        return None
    return selection == OVERWRITE_EXISTING


def ask_loading_option():
    """Asks whether to load every type or to pick types per family.

    Returns:
        str | None: name of the FamilyLoader method to call,
            None if the user cancelled
    """
    selection = forms.CommandSwitchWindow.show(
        LOADING_OPTIONS.keys(),
        message="Select loading option:",
    )
    logger.debug("Selected loading option: {}".format(selection))
    return LOADING_OPTIONS.get(selection)


def load_families(paths, loading_option, overwrite):
    """Loads the given families, reporting progress and allowing cancellation.

    A family only counts as overwritten once the loader confirms it was
    loaded, so a refused or cancelled reload is never reported as one.

    The project is scanned for loaded families once up front and again
    after each load attempt. Families that are skipped without loading cost
    no scan, and a family that arrives as a nested side effect of an earlier
    load is still recognised when its own turn comes.

    Args:
        paths (list[str]): absolute paths of the family files to load
        loading_option (str): name of the FamilyLoader method to call
        overwrite (bool): reload families that are already in the project
            instead of skipping them

    Returns:
        LoadOutcome: families that were overwritten, left untouched, and
            the ones Revit refused or the user cancelled
    """
    overwritten = set()
    skipped = set()
    failed = set()
    loaded_names = get_loaded_family_names()
    max_value = len(paths)
    with forms.ProgressBar(
        title="Loading Family {value} of {max_value}", cancellable=True
    ) as pb:
        for count, path in enumerate(paths, 1):
            if pb.cancelled:
                break
            pb.update_progress(count, max_value)

            family = FamilyLoader(path, overwrite=overwrite)
            logger.debug("Loading family: {}".format(family.name))
            was_loaded = family.name in loaded_names
            if was_loaded and not overwrite:
                logger.debug("Family is already loaded: {}".format(family.path))
                skipped.add(family)
                continue

            loaded = getattr(family, loading_option)()
            loaded_names = get_loaded_family_names()
            if not loaded:
                failed.add(family)
            elif was_loaded:
                overwritten.add(family)
    return LoadOutcome(overwritten, skipped, failed)


def report_outcome(outcome):
    """Prints what happened to the families that needed reporting.

    Args:
        outcome (LoadOutcome): result of load_families
    """
    print_family_paths("Families that were overwritten:", outcome.overwritten)
    print_family_paths(
        "Families that were already loaded and skipped:", outcome.skipped
    )
    print_family_paths("Families that were not loaded:", outcome.failed)


def print_family_paths(title, families):
    """Prints a titled list of family paths, or nothing when the set is empty.

    Args:
        title (str): heading printed above the paths
        families (set[FamilyLoader]): families to list
    """
    if not families:
        return
    output.print_md("### {}".format(title))
    for family in sorted(families):
        print(family.path)


def main():
    """Collects the user input and loads the selected families."""
    directory = forms.pick_folder("Select parent folder of families")
    logger.debug("Selected parent folder: {}".format(directory))
    if directory is None:
        logger.debug("No directory selected.")
        return

    paths = ask_families(collect_family_paths(directory))
    if paths is None:
        logger.debug("No families selected.")
        return

    overwrite = ask_overwrite(paths)
    if overwrite is None:
        logger.debug("No option selected for existing families.")
        return

    loading_option = ask_loading_option()
    if loading_option is None:
        logger.debug("No loading option selected.")
        return

    report_outcome(load_families(paths, loading_option, overwrite))


if __name__ == "__main__":
    main()
