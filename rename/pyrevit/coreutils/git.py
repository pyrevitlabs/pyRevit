"""
Description:
LibGit2Sharp wrapper module for pyRevit.

Documentation:
https://github.com/libgit2/libgit2sharp/wiki
"""

import clr
import importlib

# noinspection PyUnresolvedReferences
import System

from pyrevit.coreutils.logger import get_logger

GIT_LIB = 'LibGit2Sharp'

# todo: figure out how to import extensions on the caller's scope.
clr.AddReference("System.Core")
clr.ImportExtensions(System.Linq)
clr.AddReferenceByName(GIT_LIB)


logger = get_logger(__name__)


# public git module
git = importlib.import_module(GIT_LIB)


class RepoInfo:
    """
    Generic repo wrapper for passing repository information to other modules

    """
    def __init__(self, repo):
        self.directory = repo.Info.WorkingDirectory
        self.head_name = repo.Head.Name
        self.last_commit_hash = repo.Head.Tip.Id.Sha
        self.repo = repo


def get_repo(repo_dir):
    """

    Args:
        repo_dir:

    Returns:
        RepoInfo:
    """
    repo = git.Repository(repo_dir)
    return RepoInfo(repo)
