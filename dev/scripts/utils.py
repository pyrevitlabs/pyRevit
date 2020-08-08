"""Dev scripts utilities"""
from typing import List, Optional, Dict
import subprocess


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


def system(args: List[str], cwd: Optional[str] = None):
    """Run a command and return the stdout"""
    res = subprocess.run(args, capture_output=True, check=True, cwd=cwd)
    return res.stdout.decode().strip()


def run_command(commands: List[Command], args: Dict[str, str]):
    """Process cli args and run the appropriate commands"""
    for cmd in commands:
        if args[cmd.name]:
            cmd.run(args)
