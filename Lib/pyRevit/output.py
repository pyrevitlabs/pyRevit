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
    """Traces back the stack to find the __window__ variable in the caller local stack.
    PyRevitLoader defines __revit__ in builtins and __window__ in locals. Thus, module have access to
    __revit__ but not to __window__. This function finds __window__ in the caller stack.
    """
    frame = inspect.stack()[1][0]
    while name not in frame.f_locals:
        frame = frame.f_back
        if frame is None:
            return None
    return frame.f_locals[name]


class PyRevitConsoleWindow(object):
    """Wrapper to interact with the output console window."""
    def __init__(self, window_handle):
        self.win_handle = window_handle

    def set_title(self):
        # todo
        self.win_handle.Hide()

    def set_width(self, width):
        self.win_handle.Width = width

    def close(self):
        self.win_handle.Close()

    def hide(self):
        self.win_handle.Hide()

    def show(self):
        # todo
        self.win_handle.Show()


# creates an instance of PyRevitConsoleWindow with the recovered __window__ handler.
output_window = PyRevitConsoleWindow(_calling_scope_variable('__window__'))
