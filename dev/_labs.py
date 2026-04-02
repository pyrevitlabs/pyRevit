"""Manage pyRevit labs tasks"""
# pylint: disable=invalid-name,broad-except
import sys
import io
import os
import os.path as op
import logging
import shutil
import tempfile
from typing import Dict, List, Optional

# Configure UTF-8 encoding for console output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# dev scripts
from scripts import utils
from scripts import configs

import _install as install


logger = logging.getLogger()


def _abort(message):
    print("Build failed")
    print(message)
    sys.exit(1)


def _build(
    name: str,
    sln: str,
    config: str = "Release",
    framework: str = None,
    publish_dir: str = None,
    print_output: Optional[bool] = False,
    extra_publish_args: Optional[List[str]] = None,
):
    utils.ensure_windows()

    # clean
    slnpath = op.abspath(sln)
    logger.debug("building %s solution: %s, configuration: %s", name, slnpath, config)
    # clean, restore, build
    if publish_dir is None:
        print(f"Building {name}...")
        report = utils.system(
            [
                install.get_tool("dotnet"),
                "build",
                slnpath,
                "-c",
                f"{config}",
            ],
            dump_stdout=print_output
        )
    else:
        print(f"Publish {name}...")
        cmd = [
            install.get_tool("dotnet"),
            "publish",
            f"{slnpath}",
            "-c",
            f"{config}",
            "-f",
            f"{framework}",
            "-o",
            f"{publish_dir}",
        ]
        if extra_publish_args:
            cmd.extend(extra_publish_args)
        report = utils.system(cmd, dump_stdout=print_output)

    passed, report = utils.parse_dotnet_build_output(report)
    if not passed:
        _abort(report)
    else:
        print(f"Building {name} completed successfully")


def _merge_publish_into_bin(source_root: str, dest_bin: str) -> None:
    """Copy a dotnet publish output tree into dest_bin without deleting other files."""
    source_root = op.abspath(source_root)
    dest_bin = op.abspath(dest_bin)
    if not op.isdir(source_root):
        return
    for root, _, files in os.walk(source_root):
        rel = op.relpath(root, source_root)
        dest_dir = dest_bin if rel == "." else op.join(dest_bin, rel)
        os.makedirs(dest_dir, exist_ok=True)
        for name in files:
            dest_file = op.join(dest_dir, name)
            if op.exists(dest_file):
                print(f"  [merge] overwriting {op.relpath(dest_file, dest_bin)}")
            shutil.copy2(op.join(root, name), dest_file)


def build_deps(_: Dict[str, str]):
    """Build pyRevit deps"""
    _build("MahApps.Metro (styles)", configs.MAHAPPS, framework="net47")
    _build("MahApps.Metro (netfx)", configs.MAHAPPS, framework="net47", publish_dir=configs.LIBSPATH_NETFX)
    _build("MahApps.Metro (netcore)", configs.MAHAPPS, framework="netcoreapp3.1", publish_dir=configs.LIBSPATH_NETCORE)

    _build("Newtonsoft.Json (netfx)", configs.NEWTONSOFTJSON, framework="net45", publish_dir=configs.LIBSPATH_NETFX)
    _build("Newtonsoft.Json (netcore)", configs.NEWTONSOFTJSON, framework="net6.0", publish_dir=configs.LIBSPATH_NETCORE)

    _build("NLog (netfx)", configs.NLOG, framework="net46", publish_dir=configs.LIBSPATH_NETFX)
    _build("NLog (netcore)", configs.NLOG, framework="netstandard2.0", publish_dir=configs.LIBSPATH_NETCORE)

    _build("IronPython2 (netfx)", configs.IRONPYTHON2, framework="net48", publish_dir=configs.ENGINES2PATH_NETFX)
    _build("IronPython2 (netcore)", configs.IRONPYTHON2_LIB, framework="netstandard2.0", publish_dir=configs.ENGINES2PATH_NETCORE)
    _build("IronPython2 (netcore)", configs.IRONPYTHON2_MODULES, framework="netstandard2.0", publish_dir=configs.ENGINES2PATH_NETCORE)
    _build("IronPython2 (netcore)", configs.IRONPYTHON2_SQLITE, framework="netstandard2.0", publish_dir=configs.ENGINES2PATH_NETCORE)
    _build("IronPython2 (netcore)", configs.IRONPYTHON2_WPF, framework="net6.0-windows", publish_dir=configs.ENGINES2PATH_NETCORE)

    # NOTE: Enable when produced custom IronPython3 build
    # _build("IronPython3 (netfx)", configs.IRONPYTHON3, framework="net48", publish_dir=configs.ENGINES3PATH_NETFX)
    # _build("IronPython3 (netcore)", configs.IRONPYTHON3_LIB, framework="net6.0", publish_dir=configs.ENGINES3PATH_NETCORE)
    # _build("IronPython3 (netcore)", configs.IRONPYTHON3_MODULES, framework="net6.0", publish_dir=configs.ENGINES3PATH_NETCORE)
    # _build("IronPython3 (netcore)", configs.IRONPYTHON3_SQLITE, framework="net6.0", publish_dir=configs.ENGINES3PATH_NETCORE)
    # _build("IronPython3 (netcore)", configs.IRONPYTHON3_WPF, framework="net6.0-windows", publish_dir=configs.ENGINES3PATH_NETCORE)

    _build("Python.Net (netfx)", configs.CPYTHONRUNTIME, framework="netstandard2.0", publish_dir=configs.LIBSPATH_NETFX)
    _build("Python.Net (netcore)", configs.CPYTHONRUNTIME, framework="netstandard2.0", publish_dir=configs.LIBSPATH_NETCORE)



def build_engines(args: Dict[str, str]):
    """Build pyRevit engines."""
    config = args.get("<config>") or "Release"
    _build("loaders", configs.LOADERS, config=config)


def build_labs(args: Dict[str, str]):
    """Build pyRevit labs."""
    config = args.get("<config>") or "Release"
    _build("labs", configs.LABS, config=config)
    # Publishing two exes to the same folder breaks the second run: dotnet publish removes assemblies
    # not produced by that project (e.g. DocoptNet.dll is CLI-only and disappears if doctor publishes last).
    os.makedirs(configs.BINPATH, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        cli_dir = op.join(tmp, "cli")
        doctor_dir = op.join(tmp, "doctor")
        _build("cli", configs.LABS_CLI, config=config, framework="net8.0-windows", publish_dir=cli_dir)
        _build("doctor", configs.LABS_DOCTOR, config=config, framework="net8.0-windows", publish_dir=doctor_dir)
        print("Merging cli and doctor publish output into bin...")
        _merge_publish_into_bin(doctor_dir, configs.BINPATH)
        _merge_publish_into_bin(cli_dir, configs.BINPATH)
        print("Merged publish output into bin completed successfully")


def build_runtime(args: Dict[str, str]):
    """Build pyRevit runtime."""
    config = args.get("<config>") or "Release"
    
    IPY2712PR = "IPY2712PR"
    IPY342 = "IPY342"
    
    _build(f"runtime {IPY2712PR}", configs.RUNTIME, config=config + f" {IPY2712PR}")
    _build(f"runtime {IPY342}", configs.RUNTIME, config=config + f" {IPY342}")
