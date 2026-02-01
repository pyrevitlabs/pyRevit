"""Manage pyRevit release tasks"""
# pylint: disable=invalid-name,broad-except
import sys
import os
import os.path as op
import uuid
import json
import re
import logging
import hashlib
import base64
import tempfile
from typing import Dict, List
from collections import namedtuple
import xml.etree.ElementTree as ET

from scripts import configs
from scripts import utils

import _install as install
import _build as build
import _props as props


logger = logging.getLogger()


PyRevitCertificate = namedtuple(
    "PyRevitCertificate", "name,filename,password,contents,fingerprint"
)
PyRevitProduct = namedtuple("PyRevitProduct", "product,release,version,key")


def _abort(message):
    print("Release failed")
    print(message)
    sys.exit(1)


def _get_new_product_code():
    return str(uuid.uuid4())


def _installer_set_uuid(product_code: str, installer_files: List[str]):
    uuid_finder = re.compile(
        r"^#define MyAppUUID \"(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})\""
    )
    for installer_file in installer_files:
        contents = []
        file_changed = False
        with open(installer_file, "r") as instfile:
            logger.debug(
                "Setting uuid in file %s to %s", installer_file, product_code
            )
            for cline in instfile.readlines():
                if uuid_finder.match(cline):
                    newcline = uuid_finder.sub(
                        f'#define MyAppUUID "{product_code}"', cline
                    )
                    if cline != newcline:
                        file_changed = True
                    contents.append(newcline)
                else:
                    contents.append(cline)
        if file_changed:
            with open(installer_file, "w") as instfile:
                instfile.writelines(contents)


def _msi_set_uuid(
    product_code: str, upgrade_code: str, installer_files: List[str]
):
    for installer_file in installer_files:
        namespace = "http://schemas.microsoft.com/developer/msbuild/2003"
        dom = ET.parse(installer_file)
        ET.register_namespace("", namespace)
        nuget = dom.getroot()
        id_tag = nuget.findall(rf".//{{{namespace}}}ProductIdCode")[0]
        upgrade_tag = nuget.findall(rf".//{{{namespace}}}ProductUpgradeCode")[0]
        id_tag.text = product_code
        upgrade_tag.text = upgrade_code
        dom.write(installer_file, encoding="utf-8", xml_declaration=True)


def _update_product_data_file(ver, key, cli=False, msi=False):
    pdata = []
    with open(configs.PYREVIT_PRODUCTS_DATAFILE, "r") as dfile:
        pdata = json.load(dfile, object_hook=lambda d: PyRevitProduct(**d))

    if cli:
        product_name = "pyRevit CLI MSI" if msi else "pyRevit CLI"
        if any(x for x in pdata if x.product == product_name and x.version == ver):
            _abort(f"{product_name} product already exists with {ver=}")

        first_cli = next((x for x in pdata if "CLI" in x.product), None)
        if first_cli:
            index = pdata.index(first_cli)
        else:
            # If no CLI entries exist yet, add after all pyRevit entries
            index = next((i for i, x in enumerate(pdata) if x.product != "pyRevit"), len(pdata))

        pdata.insert(
            index,
            PyRevitProduct(
                product=product_name, release=ver, version=ver, key=key
            ),
        )

    else:
        if any(x for x in pdata if x.product == "pyRevit" and x.version == ver):
            _abort(f"pyRevit product already exists with {ver=}")

        pdata.insert(
            0,
            PyRevitProduct(
                product="pyRevit", release=ver, version=ver, key=key
            ),
        )

    with open(configs.PYREVIT_PRODUCTS_DATAFILE, "w") as dfile:
        json.dump([x._asdict() for x in pdata], dfile, indent=True)


def set_product_data(_: Dict[str, str]):
    """Set product codes on MSI installers and update product database.
    
    Inno Setup installers use stable GUIDs defined in .iss files (not updated here).
    MSI installers require new ProductCode per version (upgrade code stays same).
    """
    # Use stable GUIDs for Inno Setup installers (defined in .iss files)
    # These must match the AppId values to ensure proper version detection and upgrades
    pyrevit_inno_pc = configs.PYREVIT_INNO_PRODUCT_CODE
    pyrevitcli_inno_pc = configs.PYREVIT_CLI_INNO_PRODUCT_CODE
    
    # MSI installers require new ProductCode per version (upgrade code stays same)
    pyrevitcli_msi_pc = _get_new_product_code()

    # update product info on MSI installer files
    # Note: Only pyRevit CLI has MSI installers (PYREVIT_MSI_PROPS_FILES is empty)
    _msi_set_uuid(
        pyrevitcli_msi_pc,
        configs.PYREVIT_CLI_UPGRADE_CODE,
        configs.PYREVIT_CLI_MSI_PROPS_FILES,
    )

    build_version = props.get_version()

    # Save product codes to database for version tracking:
    # - Inno Setup installers use stable GUIDs for proper version detection
    # - MSI installers get new ProductCodes per MSI specification
    _update_product_data_file(build_version, pyrevit_inno_pc)
    _update_product_data_file(build_version, pyrevitcli_inno_pc, cli=True)
    # Save MSI ProductCode separately for pyRevit CLI MSI installer tracking
    _update_product_data_file(build_version, pyrevitcli_msi_pc, cli=True, msi=True)


def _get_binaries():
    for dirname, _, files in os.walk(configs.BINPATH):
        for fn in files:
            bf = fn.lower()
            if bf.startswith("pyrevit") and any(
                bf.endswith(x) for x in [".exe", ".dll"]
            ):
                yield op.join(dirname, fn)


def _get_cert_info():
    cert_name = os.environ.get("CERTIFICATENAME", "")
    if not cert_name:
        print("CERTIFICATENAME is required")
        sys.exit(1)

    cert_filename = op.join(tempfile.gettempdir(), "certificate.pfx")

    cert_password = os.environ.get("CERTIFICATEPASSWORD", "")
    if not cert_password:
        print("CERTIFICATEPASSWORD is required")
        sys.exit(1)

    cert_contents = os.environ.get("CERTIFICATE", "")
    if not cert_contents:
        print("CERTIFICATE is required")
        sys.exit(1)

    cert_fingerprint = os.environ.get("CERTIFICATESHA1", "")
    if not cert_fingerprint:
        print("CERTIFICATESHA1 is required")
        sys.exit(1)

    return PyRevitCertificate(
        name=cert_name,
        filename=cert_filename,
        password=cert_password,
        contents=cert_contents,
        fingerprint=cert_fingerprint,
    )


def setup_certificate(_: Dict[str, str]):
    """Add certificate to store
    needs CERTIFICATE and CERTIFICATEPASSWORD env vars
    """
    cert = _get_cert_info()
    with open(cert.filename, "wb") as certfile:
        certfile.write(base64.decodebytes(bytes(cert.contents, "utf-8")))
    utils.system(
        [
            install.get_tool("certutil"),
            "-f",
            "-p",
            f"{cert.password}",
            "-importpfx",
            f"{cert.filename}",
        ],
        dump_stdout=True,
    )


def _sign_binary(filepath: str, cert_name: str, cert_fingerprint: str):
    res, _ = utils.system(
        [
            install.get_tool("signtool"),
            "sign",
            "/sm",
            "/tr",
            "http://timestamp.digicert.com",
            "/td",
            "SHA256",
            "/sha1",
            cert_fingerprint,
            "/n",
            cert_name,
            f"{filepath}",
        ],
        dump_stdout=False,
    )
    if "SignTool Error:" in res:
        print(f"Error signing {filepath}")
        print(f"{cert_name=}")
        print(f"{cert_fingerprint=}")
        print(f"signtool results:\n{res}")
        sys.exit(1)


def _sign_nupkg(filepath: str, cert_path: str, cert_password: str):
    utils.system(
        [
            install.get_tool("nuget"),
            "sign",
            filepath,
            "-CertificatePath",
            cert_path,
            "-CertificatePassword",
            cert_password,
            "-Timestamper",
            "http://timestamp.digicert.com",
        ],
        dump_stdout=True,
    )


def sign_binaries(_: Dict[str, str]):
    """Sign binaries with certificate (must be installed on machine)"""
    print("digitally signing binaries...")
    cert = _get_cert_info()
    for bin_file in _get_binaries():
        _sign_binary(bin_file, cert.name, cert.fingerprint)


def _ensure_clean_tree():
    res, _ = utils.system(["git", "status"])
    if "nothing to commit" not in res:
        print("You have uncommited changes in working tree. Commit those first")
        sys.exit(1)


def _build_installers():
    installer = install.get_tool("iscc")
    for script in configs.INSTALLER_FILES:
        installer_script = op.abspath(script)
        print(f"Building installer {installer_script}")
        utils.system([installer, installer_script], dump_stdout=True)


def _build_msi_installers():
    installer = install.get_tool("msbuild")
    for script in configs.MSI_INSTALLER_FILES:
        installer_script = op.abspath(script)
        print(f"Building installer {installer_script}")
        utils.system([installer, installer_script], dump_stdout=True)


def _build_choco_packages():
    build_version_urlsafe = props.get_version(install=False, url_safe=True)
    base_url = (
        "https://github.com/pyrevitlabs/pyRevit/"
        f"releases/download/v{build_version_urlsafe}/"
    )
    install_version = props.get_version(install=True)
    pyrevit_cli_admin_installer = (
        configs.PYREVIT_CLI_ADMIN_INSTALLER_NAME.format(version=install_version)
        + ".exe"
    )

    download_url = base_url + pyrevit_cli_admin_installer
    sha256_hash = hashlib.sha256()
    installer_file = op.join(
        configs.DISTRIBUTE_PATH, pyrevit_cli_admin_installer
    )
    with open(installer_file, "rb") as f:
        # read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
        sha256_hash = str(sha256_hash.hexdigest()).upper()

    contents = []
    url_finder = re.compile(r"\$url64\s+=")
    checksum64_finder = re.compile(r"  checksum64\s+=")
    with open(configs.PYREVIT_CHOCO_INSTALL_FILE, "r") as cifile:
        for cline in cifile.readlines():
            if url_finder.match(cline):
                contents.append(f"$url64      = '{download_url}'\n")
            elif checksum64_finder.match(cline):
                contents.append(f"  checksum64    = '{sha256_hash}'\n")
            else:
                contents.append(cline)

    with open(configs.PYREVIT_CHOCO_INSTALL_FILE, "w") as cifile:
        cifile.writelines(contents)

    print("Building choco package...")
    utils.system(
        [
            install.get_tool("choco"),
            "pack",
            configs.PYREVIT_CHOCO_NUSPEC_FILE,
            "--outdir",
            "dist",
        ],
        dump_stdout=True,
    )


def build_installers(_: Dict[str, str]):
    """Build pyRevit and CLI installers"""
    _build_installers()
    _build_msi_installers()
    _build_choco_packages()


def sign_installers(_: Dict[str, str]):
    """Sign installers with certificate (must be installed on machine)"""
    print("digitally signing installers...")
    cert = _get_cert_info()
    install_version = props.get_version(install=True)
    for installer_exe_fmt in configs.INSTALLER_EXES:
        installer_exe = installer_exe_fmt.format(version=install_version)
        _sign_binary(f"{installer_exe}.exe", cert.name, cert.fingerprint)

    for installer_msi_fmt in configs.INSTALLER_MSIS:
        installer_msi = installer_msi_fmt.format(version=install_version)
        _sign_binary(f"{installer_msi}.msi", cert.name, cert.fingerprint)

    installer_nupkg = configs.PYREVIT_CHOCO_NUPKG_FILE.format(
        version=install_version
    )
    _sign_nupkg(installer_nupkg, cert.filename, cert.password)


def create_release(args: Dict[str, str]):
    """Create pyRevit release (build all projects, create installers)"""
    utils.ensure_windows()

    # run a check on all tools
    if not install.check(args):
        _abort("At least one necessary tool is missing for release process")

    # update copyright notice
    props.set_year(args)

    # update release version
    # prepare required arg for props.set_ver
    args["<ver>"] = args["<tag>"]
    props.set_ver(args)

    # update product data
    set_product_data(args)

    # now build all projects
    build.build_binaries(args)

    # sign everything
    sign_binaries(args)

    # now build the installers
    build_installers(args)

    # now sign installers
    sign_installers(args)


def _commit_changes(msg):
    for commit_file in configs.COMMIT_FILES:
        utils.system(["git", "add", commit_file])
    utils.system(["git", "commit", "-m", msg])


def _tag_changes():
    build_version = props.get_version()
    utils.system(["git", "tag", f"v{build_version}"])
    utils.system(["git", "tag", f"cli-v{build_version}"])


def commit_and_tag_build(_: Dict[str, str]):
    """Commit changes and tag repo"""
    _commit_changes("Publish!")
    _tag_changes()
