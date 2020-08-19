"""Set various metadata properties across source files"""
import sys
import os
import os.path as op
from typing import Dict, List
import re
import datetime
import ast
import yaml

from scripts import configs
from scripts import utils
from scripts import airtavolo


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
        with open(verfile, "r") as vfile:
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
        print(utils.colorize("<red>Invalid version format (e.g. 4.8.0)</red>"))
        sys.exit(1)


def _find_toolbundles(root_path) -> List[str]:
    tbfinder = re.compile(r".+\..+")
    scfinder = re.compile(r".*script\.py")
    tbundles = []
    for entry in os.listdir(root_path):
        epath = op.join(root_path, entry)
        if op.isdir(epath) and tbfinder.match(entry):
            if any(scfinder.match(x) for x in os.listdir(epath)):
                tbundles.append(epath)
            else:
                tbundles.extend(_find_toolbundles(epath))
    return tbundles


def _extract_bundle_title(bundle_dict):
    title_data = bundle_dict.get("title", None)
    if isinstance(title_data, dict):
        # find english name
        return title_data.get("en_us", None) or title_data.get("english", None)
    elif isinstance(title_data, str):
        # assume english?!
        return title_data


def _find_tlocale(bundle_title: str, tool_locales) -> airtavolo.ToolLocales:
    for tlocale in tool_locales:
        if bundle_title == tlocale.name:
            return tlocale


def _prepare_title_data(langs_dict):
    tdata = {}
    lcode_finder = re.compile(r".+\s*\[(.+)\]")
    for lang, tvalue in langs_dict.items():
        if lcode := lcode_finder.match(lang):
            tdata[lcode.groups()[0]] = tvalue
    return tdata


def _update_toolbundle_locales(
    bundle_path, tool_locales: List[airtavolo.ToolLocales]
):
    blfinder = re.compile(r"(.*bundle\.yaml)")
    bundlefile_match = next(
        (x for x in os.listdir(bundle_path) if blfinder.match(x)), None
    )
    # if bundle file exist, load and find the english title
    # search tool_locales for one with matching title
    # create the locale dict and update the existing
    if bundlefile_match:
        bundle_file = op.join(bundle_path, bundlefile_match)
        # read existing bundle
        with open(bundle_file, "r") as bfile:
            bundle_dict = yaml.load(bfile, Loader=yaml.SafeLoader)
        title = _extract_bundle_title(bundle_dict)
        if title:
            tlocale = _find_tlocale(title, tool_locales)
            if tlocale:
                title_dict = bundle_dict["title"]
                if isinstance(title_dict, str):
                    title_dict = {"en_us": title_dict}
                # apply new values
                title_dict.update(_prepare_title_data(tlocale.langs))
                bundle_dict["title"] = title_dict
                # write back changes
                with open(bundle_file, "w") as bfile:
                    yaml.dump(bundle_dict, bfile, allow_unicode=True)
    # # otherwise if there is data for this bundle
    # # create the bundle file and dump data
    # else:
    #     bundle_file = op.join(bundle_path, "bundle.yaml")
    #     # grab name from bundle
    #     title = op.splitext(op.basename(bundle_path))[0]
    #     tlocale = _find_tlocale(title, tool_locales)
    #     if tlocale:
    #         bundle_dict = {"title": _prepare_title_data(tlocale.langs)}
    #         with open(bundle_file, "w") as bfile:
    #             yaml.dump(bundle_dict, bfile)


# TODO: find a list of all bundles with their names
# TODO: for each tool locale, lookup the bundle
# TODO: write in yaml files only?
def update_locales(_: Dict[str, str]):
    """Update locale files across the extensions"""
    tool_locales = airtavolo.get_tool_locales()
    for tbundle in _find_toolbundles(configs.EXTENSIONS_PATH):
        _update_toolbundle_locales(tbundle, tool_locales)
