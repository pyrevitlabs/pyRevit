"""Misc build functions"""
from typing import Dict

from scripts import configs
from scripts import utils


def count_sloc(_: Dict[str, str]):
    """Count SLOC across pyRevit source codes"""
    print("Counting single lines of code...")
    counter_args = ['pygount', '--format=summary', '--suffix=cs,py,go']
    counter_args.extend(configs.SOURCE_DIRS)
    report = utils.system(counter_args)
    print(report)
