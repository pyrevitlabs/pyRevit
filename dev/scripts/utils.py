"""Dev scripts utilities"""
# pylint: disable=bad-continuation
import sys
import os
import os.path as op
import logging
import re
from typing import List, Optional, Dict
import subprocess


logger = logging.getLogger()


class Command:
    """CLI command type"""

    def __init__(self, name, target, args, run):
        self.name = name
        self.target = target
        self.args = args
        self.help = run.__doc__
        self.template = " ".join(
            [x for x in [self.name, self.target, " ".join(self.args)] if x]
        )
        self.run = run

    def __repr__(self):
        return f"[{self.name} {self.target}]"


def system(
    args: List[str],
    cwd: Optional[str] = None,
    dump_stdout: Optional[bool] = False,
):
    """Run a command and return the stdout"""
    if dump_stdout:
        res = subprocess.run(
            args, stderr=subprocess.STDOUT, check=False, cwd=cwd
        )
        return ""
    else:
        res = subprocess.run(args, capture_output=True, check=False, cwd=cwd)
        return res.stdout.decode().strip()


def where(program_name):
    """Test if a program is available on PATH"""
    if op.exists(program_name) \
            or (sys.platform == "win32" and op.exists(program_name + ".exe")):
        return True

    finder = "where" if sys.platform == "win32" else "which"
    res = subprocess.run(
        [finder, program_name], check=False, capture_output=True
    )
    return res.stdout != b""


def format_help(helpstring):
    """Format command help for cli help"""
    formatted_help = helpstring
    helplines = helpstring.split("\n")
    helplines = [x.strip() for x in helplines]
    if helplines:
        formatted_help = helplines[0]
        for hline in helplines[1:]:
            if hline:
                formatted_help += f"\n{'':44}{hline}"
    return formatted_help


def run_command(commands: List[Command], args: Dict[str, str]):
    """Process cli args and run the appropriate commands"""
    for cmd in [x for x in commands if args[x.name]]:
        if cmd.target:
            if not args[cmd.target]:
                continue
        logger.debug("Running %s", cmd)
        cmd.run(args)


def parse_dotnet_build_output(output):
    """Parse dotnet build output to find the result and error reports"""
    result = True
    build_finder = re.compile(r"^Build (success.*|FAIL.*)$")
    time_finder = re.compile(r"^Time Elapsed (.+)$")
    capture = False
    report = ""
    for oline in output.split("\n"):
        if time_finder.match(oline):
            break
        if capture:
            report += f"{oline}\n"
        if match := build_finder.match(oline):
            if "fail" in match.groups()[0].lower():
                result = False
                capture = True
    return result, report


def ensure_windows():
    """Ensure utility is running on Windows"""
    if sys.platform != "win32":
        print("This command can only execute on Windows")
        sys.exit(1)


TERMINAL_CODES = {
    "b": 1,
    "f": 2,
    "red": 91,
    "grn": 92,
}


def colorize(input_string):
    """Replace <x> tags with terminal color codes
    Tag format: <x> content </x>
    Supported tags: {}
    """.format(
        ", ".join(TERMINAL_CODES.keys())
    )
    result = input_string
    for tcode, tval in TERMINAL_CODES.items():
        result = result.replace(f"<{tcode}>", f"\033[{tval}m")
        result = result.replace(f"</{tcode}>", "\033[0m")
    return result
