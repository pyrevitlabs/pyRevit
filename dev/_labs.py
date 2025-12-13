"""Manage pyRevit labs tasks"""
# pylint: disable=invalid-name,broad-except
import sys
import io
import os.path as op
import logging
from typing import Dict, Optional

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


def _build(name: str, sln: str, config: str = "Release", framework: str = None, publish_dir: str = None, print_output: Optional[bool] = False):
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
    _build("cli", configs.LABS_CLI, config=config, framework="net8.0-windows", publish_dir=configs.BINPATH)
    _build("doctor", configs.LABS_DOCTOR, config=config, framework="net8.0-windows", publish_dir=configs.BINPATH)


def build_runtime(args: Dict[str, str]):
    """Build pyRevit runtime."""
    config = args.get("<config>") or "Release"
    
    IPY2712PR = "IPY2712PR"
    IPY342 = "IPY342"
    
    _build(f"runtime {IPY2712PR}", configs.RUNTIME, config=config + f" {IPY2712PR}")
    _build(f"runtime {IPY342}", configs.RUNTIME, config=config + f" {IPY342}")
