""" Module name = output.py
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE


~~~
This module provides a wrapper class to interact with the standard text output window.
Usage.
    from pyRevit.output import output_window
    output_window.set_width(1100)
    output_window.show()
"""


import inspect


def _calling_scope_variable(name):
    """Traces back the stack to find the variable in the caller local stack.
    PyRevitLoader defines __revit__ in builtins and __window__ in locals. Thus, modules have access to
    __revit__ but not to __window__. This function is used to finds __window__ in the caller stack.
    """
    frame = inspect.stack()[1][0]
    while name not in frame.f_locals:
        frame = frame.f_back
        if frame is None:
            return None
    return frame.f_locals[name]


class PyRevitConsoleWindow:
    """Wrapper to interact with the output console window."""

    def __init__(self, window_handle):
        self.__winhandle__ = window_handle

    def set_title(self):
        # todo
        self.__winhandle__.Hide()

    def set_width(self, width):
        self.__winhandle__.Width = width

    def set_height(self, height):
        self.__winhandle__.Height = height

    def resize(self, width, height):
        self.set_width(width)
        self.set_height(height)

    # def close(self):
    #     self.__winhandle__.Close()

    def hide(self):
        self.__winhandle__.Hide()

    def show(self):
        self.__winhandle__.Show()

    def clear(self):
        """Clears the content in output window."""
        self.__winhandle__.txtStdOut.Clear()


# creates an instance of PyRevitConsoleWindow with the recovered __window__ handler.
win_handler = _calling_scope_variable('__window__')
if win_handler:
    output_window = PyRevitConsoleWindow(win_handler)
