"""Dev scripts utilities"""
from typing import List, Optional
import subprocess


def system(args: List[str], cwd: Optional[str] = None):
    """Run a command and return the stdout"""
    res = subprocess.run(args, capture_output=True, check=True, cwd=cwd)
    return res.stdout.decode().strip()
