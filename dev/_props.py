"""Set various metadata properties across source files"""
import sys
import os
import os.path as op
from typing import Dict, List
import re
import datetime
import logging
import xml.etree.ElementTree as ET

import yaml

from scripts import configs
from scripts import utils
from scripts import airtavolo
from scripts.airtavolo import ToolLocales


logger = logging.getLogger()


VER_FINDER = re.compile(r"\d\.\d+\.\d+(\.[a-z0-9+-]+)?")
VER_PART_FINDER = re.compile(r"^(\d)\.(\d+?)\.(\d+?)(\.[a-z0-9+-]+)?")


def _get_urlsafe_version(version: str):
    return version.replace("+", "%2B")


def _get_release_url(version: str):
    build_version_urlsafe = _get_urlsafe_version(version)
    return (
        "https://github.com/eirannejad/pyRevit/"
        f"releases/tag/v{build_version_urlsafe}/"
    )


def _modify_contents(files, finder, new_value):
    for text_file in files:
        contents = []
        file_changed = False
        with open(text_file, "r") as sfile:
            logger.debug(
                "Setting version in file %s to %s", text_file, new_value
            )
            for cline in sfile.readlines():
                newcline = finder.sub(new_value, cline)
                if cline != newcline:
                    file_changed = True
                contents.append(newcline)
        if file_changed:
            with open(text_file, "w") as sfile:
                sfile.writelines(contents)


def _modify_msi_year(copyright_message: str):
    msi_file = configs.PYREVIT_COMMON_MSI_PROPSFILE
    namespace = "http://schemas.microsoft.com/developer/msbuild/2003"
    dom = ET.parse(msi_file)
    ET.register_namespace("", namespace)
    nuget = dom.getroot()
    copyright_tag = nuget.findall(rf".//{{{namespace}}}Copyright")[0]
    copyright_tag.text = f"Copyright © {copyright_message}"
    dom.write(msi_file, encoding="utf-8", xml_declaration=True)


def _modify_msi_version(_: str, install_version: str):
    msi_file = configs.PYREVIT_COMMON_MSI_PROPSFILE
    namespace = "http://schemas.microsoft.com/developer/msbuild/2003"
    dom = ET.parse(msi_file)
    ET.register_namespace("", namespace)
    nuget = dom.getroot()
    version_tag = nuget.findall(rf".//{{{namespace}}}Version")[0]
    version_tag.text = install_version
    dom.write(msi_file, encoding="utf-8", xml_declaration=True)


def _modify_choco_nuspec_year(copyright_message: str):
    nuspec_file = configs.PYREVIT_CHOCO_NUSPEC_FILE
    namespace = "http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"
    dom = ET.parse(nuspec_file)
    ET.register_namespace("", namespace)
    nuget = dom.getroot()
    copyright_tag = nuget.findall(rf".//{{{namespace}}}copyright")[0]
    copyright_tag.text = f"Copyright © {copyright_message}"
    dom.write(nuspec_file, encoding="utf-8", xml_declaration=True)


def _modify_choco_nuspec_version(build_version: str, install_version: str):
    nuspec_file = configs.PYREVIT_CHOCO_NUSPEC_FILE
    releasenotes_url = _get_release_url(build_version)
    namespace = "http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"
    dom = ET.parse(nuspec_file)
    ET.register_namespace("", namespace)
    nuget = dom.getroot()
    version_tag = nuget.findall(rf".//{{{namespace}}}version")[0]
    release_notes_tag = nuget.findall(rf".//{{{namespace}}}releaseNotes")[0]
    version_tag.text = install_version
    release_notes_tag.text = releasenotes_url
    dom.write(nuspec_file, encoding="utf-8", xml_declaration=True)


def get_version(install=False, url_safe=False):
    """Get current version"""
    verfile = (
        configs.PYREVIT_INSTALL_VERSION_FILE
        if install
        else configs.PYREVIT_VERSION_FILE
    )
    with open(verfile, "r") as vfile:
        for cline in vfile.readlines():
            if match := VER_FINDER.search(cline):
                if url_safe:
                    return _get_urlsafe_version(match.group())
                return match.group()


def set_year(_: Dict[str, str]):
    """Update copyright notice"""
    today = datetime.datetime.today()
    this_year = today.year
    # this is more flexible than: if today.month == 12:
    if (datetime.datetime(this_year + 1, 1, 1) - today).days < 30:
        this_year += 1
    cp_finder = re.compile(r"2014-\d{4}")
    new_copyright = f"2014-{this_year}"
    print(f'Updating copyright notice to "{new_copyright}"...')
    _modify_contents(
        files=configs.COPYRIGHT_FILES, finder=cp_finder, new_value=new_copyright
    )
    _modify_msi_year(new_copyright)
    _modify_choco_nuspec_year(new_copyright)


def set_ver(args: Dict[str, str]):
    """Update version number"""

    def _update_build_number(version: str):
        parts = VER_PART_FINDER.findall(version)
        if parts:
            version = parts[0]
            major = version[0]
            minor = version[1]
            patch = version[2]
            build = datetime.datetime.now().strftime("%y%j+%H%M")
            return f"{major}.{minor}.{patch}.{build}"
        return version

    build_version = _update_build_number(args["<ver>"])

    # add wip to version if this is a wip build
    is_wip = args.get("<build>", "release") == "wip"
    if is_wip:
        build_version += configs.PYREVIT_WIP_VERSION_EXT

    if VER_FINDER.match(build_version):
        # update necessary files with "build version"
        print(f"Updating version to v{build_version}...")
        _modify_contents(
            files=configs.VERSION_FILES,
            finder=VER_FINDER,
            new_value=build_version,
        )

        # update installer scripts with "install version"
        install_version, _ = build_version.split("+")
        print(f"Updating installers to v{install_version}...")
        with open(configs.PYREVIT_INSTALL_VERSION_FILE, "w") as ivfile:
            ivfile.writelines(install_version)

        _modify_contents(
            files=configs.INSTALLER_FILES,
            finder=VER_FINDER,
            new_value=install_version,
        )

        _modify_choco_nuspec_version(build_version, install_version)
        _modify_msi_version(build_version, install_version)
    else:
        print(utils.colorize("<red>Invalid version format (e.g. 4.8.0)</red>"))
        sys.exit(1)


def set_build_ver(args: Dict[str, str]):
    """Generate and set new build version"""
    with open(configs.PYREVIT_VERSION_FILE, "r") as vfile:
        version = vfile.readline()
    if version:
        args["<ver>"] = version.strip()
        set_ver(args)


def _find_tbundles(root_path) -> List[str]:
    tbfinder = re.compile(r".+\..+")
    scfinder = re.compile(r".*script\.py")
    tbundles = []
    for entry in os.listdir(root_path):
        epath = op.join(root_path, entry)
        if op.isdir(epath) and tbfinder.match(entry):
            if any(scfinder.match(x) for x in os.listdir(epath)):
                tbundles.append(epath)
            else:
                tbundles.extend(_find_tbundles(epath))
    return tbundles


def _extract_title(bundle_dict):
    title_data = bundle_dict.get("title", None)
    if isinstance(title_data, dict):
        # find english name
        return title_data.get("en_us", None) or title_data.get("english", None)
    elif isinstance(title_data, str):
        # assume english?!
        return title_data


def _find_tlocale(bundle_title: str, tool_locales) -> ToolLocales:
    for tlocale in tool_locales:
        if bundle_title == tlocale.name:
            return tlocale


def _prepare_title(langs_dict):
    tdata = {}
    lcode_finder = re.compile(r".+\s*\[(.+)\]")
    for lang, tvalue in langs_dict.items():
        if lcode := lcode_finder.match(lang):
            tdata[lcode.groups()[0]] = tvalue
    return tdata


def _update_locales(bundle_path: str, tool_locales: List[ToolLocales]):
    blfinder = re.compile(r"(.*bundle\.yaml)")
    bundlefile_match = next(
        (x for x in os.listdir(bundle_path) if blfinder.match(x)), None
    )
    bundle_name = op.splitext(op.basename(bundle_path))[0]
    # if bundle file exist, load and find the english title
    # search tool_locales for one with matching title
    # create the locale dict and update the existing
    if bundlefile_match:
        bundle_file = op.join(bundle_path, bundlefile_match)
        # read existing bundle
        with open(bundle_file, "r") as bfile:
            bundle_dict = yaml.load(bfile, Loader=yaml.SafeLoader)
        title = _extract_title(bundle_dict) or bundle_name
        tlocale = _find_tlocale(title, tool_locales)
        if tlocale:
            title_dict = bundle_dict.get("title", {"en_us": title})
            if isinstance(title_dict, str):
                title_dict = {"en_us": title_dict}
            # apply new values
            title_dict.update(_prepare_title(tlocale.langs))
            bundle_dict["title"] = title_dict
            # write back changes
            with open(bundle_file, "w") as bfile:
                yaml.dump(bundle_dict, bfile, allow_unicode=True)
    # otherwise if there is data for this bundle
    # create the bundle file and dump data
    else:
        bundle_file = op.join(bundle_path, "bundle.yaml")
        # grab name from bundle
        tlocale = _find_tlocale(bundle_name, tool_locales)
        if tlocale:
            bundle_dict = {"title": _prepare_title(tlocale.langs)}
            with open(bundle_file, "w") as bfile:
                yaml.dump(bundle_dict, bfile)


def set_locales(_: Dict[str, str]):
    """Update locale files across the extensions"""
    tool_locales = airtavolo.get_tool_locales()
    for tbundle in _find_tbundles(configs.EXTENSIONS_PATH):
        _update_locales(tbundle, tool_locales)
