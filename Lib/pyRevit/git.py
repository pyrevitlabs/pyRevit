import os.path as op
import re

import pyRevit.utils as utils
import pyRevit.config as cfg
from pyRevit.exceptions import GitError
from pyRevit.logger import logger


GIT_FOLDER = '.git'


class GitRepository(object):
    """Object for handling all tasks on a local git repository.
    This class uses the portable git tool installed with pyRevit."""
    repo_name = ''
    repo_dir = ''

    def __init__(self, repo_dir):
        GitRepository._is_git_repo_dir(repo_dir)
        self.repo_dir = repo_dir
        self.repo_name = op.basename(self.repo_dir)

    @staticmethod
    def _is_git_repo_dir(repo_dir):
        # will raise GitError if .git directory does not exist under folder
        if not op.exists(op.join(repo_dir, GIT_FOLDER)):
            raise GitError(repo_dir, 'Directory is not a git repository.')

    def find_current_branch(self):
        """Returns the name of the current checked-out branch: str."""
        bfinder = re.compile('\*\s(.+)')
        output = utils.run_process(r'{0} branch'.format(cfg.GIT_EXE), cwd=self.repo_dir)
        res = bfinder.findall(output.communicate()[0])
        if len(res) > 0:
            logger.debug('Current branch is {} for git repo {} at {}'.format(res[0], self.repo_name, self.repo_dir))
            return res[0]
        else:
            raise GitError(self.repo_dir, 'Error finding branch.')

    def fetch_from_origin(self):
        try:
            utils.run_process(r'{0} fetch --all'.format(cfg.GIT_EXE), cwd=self.repo_dir)
        except:
            raise GitError(self.repo_dir, 'Error fetching from origin.')

    def git_hard_reset_to_origin(self):
        # Fetch changes
        utils.run_process(r'{0} fetch --all'.format(cfg.GIT_EXE), cwd=self.repo_dir)
        # Could get results and return: output.communicate()[0]; output.returncode

        # Hard reset current branch to origin/branch
        try:
            utils.run_process(r'{0} reset --hard origin/{1}'.format(cfg.GIT_EXE,
                                                                    self.find_current_branch()), cwd=self.repo_dir)
            # Could get results and return: output.communicate()[0]; output.returncode
        except GitError as err:
            logger.debug(err.msg)
            raise err


def get_repo(repo_dir):
    """Public function to create an instance of GitRepository for provided folder.
    This function will raise GitError if folder is not a git repository."""
    return GitRepository(repo_dir)
