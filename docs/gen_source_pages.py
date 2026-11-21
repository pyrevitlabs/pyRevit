"""Generate reference pages whose content is owned by source files.

The CLI command reference, the engine table, the deployment table and the
script result codes are read from the files the product itself uses, so the
published pages cannot drift from the code.
"""

import re
import tomllib
from collections import OrderedDict
from pathlib import Path

import mkdocs_gen_files


CLI_USAGE = Path("dev/pyRevitLabs/pyRevitCLI/Resources/UsagePatterns.txt")
PYREVITFILE = Path("pyRevitfile")
SCRIPT_EXECUTOR = Path("dev/pyRevitLabs.PyRevit.Runtime/ScriptExecutor.cs")

RESULT_CODE = re.compile(r"public static int (\w+) = (\d+);")
CAMEL_BOUNDARY = re.compile(r"(?<=[a-z])(?=[A-Z])")


def cli_commands():
    """Group the CLI usage patterns by their first command word.

    Returns:
        OrderedDict: command name mapped to its usage lines, in file order.
            Patterns without a command word (``--help``, ``--version``) are
            grouped under ``pyrevit``.
    """
    groups = OrderedDict()
    for line in CLI_USAGE.read_text(encoding="utf-8").splitlines():
        usage = line.strip()
        if not usage.startswith("pyrevit"):
            continue
        words = usage.split()
        command = words[1] if len(words) > 1 else ""
        if not re.fullmatch(r"[a-z]+", command):
            command = "pyrevit"
        groups.setdefault(command, []).append(usage)
    return groups


def write_cli_reference():
    """Write ``cli/reference.md`` with one section per CLI command."""
    with mkdocs_gen_files.open("cli/reference.md", "w") as page:
        print("# Command reference\n", file=page)
        print(
            "Every usage pattern the `pyrevit` command line accepts, generated "
            f"from `{CLI_USAGE.as_posix()}`.\n",
            file=page,
        )
        for command, usages in cli_commands().items():
            title = "General" if command == "pyrevit" else f"`{command}`"
            print(f"## {title}\n", file=page)
            print("```text", file=page)
            print("\n".join(usages), file=page)
            print("```\n", file=page)
    mkdocs_gen_files.set_edit_path("cli/reference.md", Path("../") / CLI_USAGE)


def write_engines():
    """Write ``runtime/engines.md`` from the engines in ``pyRevitfile``.

    Only engines marked ``runtime = true`` can load pyRevit, so the page
    separates the ids ``pyrevit attach`` accepts from the script-only engines.
    """
    engines = tomllib.loads(PYREVITFILE.read_text(encoding="utf-8"))["engines"]
    with mkdocs_gen_files.open("runtime/engines.md", "w") as page:
        print("# Engines\n", file=page)
        print(
            "Script engines shipped with pyRevit, generated from `pyRevitfile`.\n",
            file=page,
        )
        print(
            "A runtime engine loads pyRevit itself: `pyrevit attach` accepts its "
            "engine id, and `default` selects the `DEFAULT` engine. A script "
            "engine only runs scripts that ask for it and cannot be attached.\n",
            file=page,
        )
        print("| Name | Engine id | Kernel | Use | Folder | Description |", file=page)
        print("|---|---|---|---|---|---|", file=page)
        for name, engine in engines.items():
            use = "Runtime, attachable" if engine.get("runtime") else "Scripts only"
            print(
                "| `{}` | `{}` | {} | {} | `{}` | {} |".format(
                    name,
                    engine["version"],
                    engine["kernel"],
                    use,
                    engine["path"],
                    engine.get("description", ""),
                ),
                file=page,
            )
    mkdocs_gen_files.set_edit_path("runtime/engines.md", Path("../") / PYREVITFILE)


def write_deployments():
    """Write ``teams/deployments.md`` from the deployments in ``pyRevitfile``."""
    deployments = tomllib.loads(PYREVITFILE.read_text(encoding="utf-8"))["deployments"]
    with mkdocs_gen_files.open("teams/deployments.md", "w") as page:
        print("# Deployments\n", file=page)
        print(
            "A deployment is a named subset of the pyRevit files. Pass its name "
            "to `pyrevit clone <clone_name> <deployment_name>` to install only "
            "those paths. Generated from `pyRevitfile`.\n",
            file=page,
        )
        for name, paths in deployments.items():
            print(f"## `{name}`\n", file=page)
            print("```text", file=page)
            print("\n".join(paths), file=page)
            print("```\n", file=page)
    mkdocs_gen_files.set_edit_path("teams/deployments.md", Path("../") / PYREVITFILE)


def write_result_codes():
    """Write ``runtime/executor-result-codes.md`` from the C# result codes."""
    codes = RESULT_CODE.findall(SCRIPT_EXECUTOR.read_text(encoding="utf-8"))
    with mkdocs_gen_files.open("runtime/executor-result-codes.md", "w") as page:
        print("# Executor result codes\n", file=page)
        print(
            "Codes the script executor returns after running a command, "
            f"generated from `{SCRIPT_EXECUTOR.as_posix()}`.\n",
            file=page,
        )
        print("| Code | Result |", file=page)
        print("|---|---|", file=page)
        for name, code in sorted(codes, key=lambda item: int(item[1])):
            print(f"| {code} | {CAMEL_BOUNDARY.sub(' ', name)} |", file=page)
    mkdocs_gen_files.set_edit_path(
        "runtime/executor-result-codes.md", Path("../") / SCRIPT_EXECUTOR
    )


write_cli_reference()
write_engines()
write_deployments()
write_result_codes()
