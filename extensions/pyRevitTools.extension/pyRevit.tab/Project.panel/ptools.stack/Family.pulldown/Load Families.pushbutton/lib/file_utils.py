# -*- coding: utf-8 -*-
""" Module to search for files in a directory """
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import re
import os
import itertools
import fnmatch

from pyrevit import script, forms

logger = script.get_logger()


class FileFinder:
    """
    Handles the file search in a directory

    Attributes
    ----------
    directory : str
        Path of the target directory
    paths : set()
        Holds absolute paths of search result

    Methods
    -------
    search(str)
        Searches in the target directory for the given glob pattern.
        Adds absolute paths to self.paths.

    exclude_by_pattern(str)
        Filters self.paths by the given regex pattern.
    """
    def __init__(self, directory):
        """
        Parameters
        ----------
        directory : str
            Absolute path to target directory.
        """
        self.directory = directory
        self.paths = set()

    def search(self, pattern):
        """
        Searches in the target directory for the given glob pattern.
        Adds absolute paths to self.paths.

        Parameters
        ----------
        pattern : str
            Glob pattern
        """
        for root, _, files in os.walk(self.directory):
            for filename in fnmatch.filter(files, pattern):
                path = os.path.join(root, filename)
                logger.debug('Found file: {}'.format(path))
                self.paths.add(path)

        if len(self.paths) == 0:
            logger.debug(
                'No {} files in "{}" found.'.format(pattern, self.directory))
            forms.alert(
                'No {} files in "{}" found.'.format(pattern, self.directory))
            script.exit()

    def exclude_by_pattern(self, pattern):
        """
        Filters self.paths by the given regex pattern.

        Parameters
        ----------
        pattern : str
            Regular expression pattern
        """
        self.paths = itertools.ifilterfalse(    #pylint: disable=no-member
            re.compile(pattern).match, self.paths)
