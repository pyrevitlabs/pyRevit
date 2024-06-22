"""Manage pyRevit labs tasks"""
# pylint: disable=invalid-name,broad-except
import sys
import os.path as op
import logging
from typing import Dict, Optional

# dev scripts
from scripts import utils
from scripts import configs

import _install as install


logger = logging.getLogger()


def _abort(message):
    print("Build failed")
    print(message)
    sys.exit(1)


def _build(name: str, sln: str, config: str = "Release", framework: str = None, publish_dir: str = None, print_output: Optional[bool] = False):
    utils.ensure_windows()

    # clean
    slnpath = op.abspath(sln)
    logger.debug("building %s solution: %s", name, slnpath)
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
        report = utils.system(
            [
                install.get_tool("dotnet"),
                "publish",
                f"{slnpath}",
                "-c",
                f"{config}",
                "-f",
                f"{framework}",
                "-o",
                f"{publish_dir}",
            ],
            dump_stdout=print_output
        )

    passed, report = utils.parse_dotnet_build_output(report)
    if not passed:
        _abort(report)
    else:
        print(f"Building {name} completed successfully")


def build_deps(_: Dict[str, str]):
    """Build pyRevit deps"""
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

    _build("IronPython3 (netfx)", configs.IRONPYTHON3, framework="net48", publish_dir=configs.ENGINES3PATH_NETFX)
    _build("IronPython3 (netcore)", configs.IRONPYTHON3_LIB, framework="net6.0", publish_dir=configs.ENGINES3PATH_NETCORE)
    _build("IronPython3 (netcore)", configs.IRONPYTHON3_MODULES, framework="net6.0", publish_dir=configs.ENGINES3PATH_NETCORE)
    _build("IronPython3 (netcore)", configs.IRONPYTHON3_SQLITE, framework="net6.0", publish_dir=configs.ENGINES3PATH_NETCORE)
    _build("IronPython3 (netcore)", configs.IRONPYTHON3_WPF, framework="net6.0-windows", publish_dir=configs.ENGINES3PATH_NETCORE)



def build_engines(_: Dict[str, str]):
    """Build pyRevit engines"""
    _build("loaders", configs.LOADERS, "Release")
    _build("cpython 3.8.5 engine", configs.CPYTHONRUNTIME, "Release")


def build_labs(_: Dict[str, str]):
    """Build pyRevit labs"""
    _build("labs", configs.LABS, "Release")
    _build("cli", configs.LABS_CLI, "Release", "net8.0-windows", configs.BINPATH)
    _build("doctor", configs.LABS_DOCTOR, "Release", "net8.0-windows", configs.BINPATH)


def build_runtime(_: Dict[str, str]):
    """Build pyRevit runtime"""
    _build("runtime", configs.RUNTIME, "Release")
