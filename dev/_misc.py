"""Misc build functions"""
from typing import Dict

from scripts import configs
from scripts import utils
from scripts import github


def count_sloc(_: Dict[str, str]):
    """Count SLOC across pyRevit source codes"""
    print("Counting single lines of code...")
    counter_args = ['pygount', '--format=summary', '--suffix=cs,py,go']
    counter_args.extend(configs.SOURCE_DIRS)
    report = utils.system(counter_args)
    print(report)


def report_dls(_: Dict[str, str]):
    """Report downloads on latest release assets
    Queries github release information to find download counts, so
    GITHUBAUTH env var must contain access token for github API.
    Otherwise access will be limited to github api rate limits
    """
    print("Collecting download info...")
    print("-"*64)
    for release in github.get_releases():
        if release.assets:
            for asset in release.assets:
                print(f'{asset.name:<48}{asset.downloads:>16}')
