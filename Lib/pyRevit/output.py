import inspect


def _calling_scope_variable(name):
    frame = inspect.stack()[1][0]
    while name not in frame.f_locals:
        frame = frame.f_back
        if frame is None:
            return None
    return frame.f_locals[name]


class PyRevitConsoleWindow(object):
    def __init__(self, window_handle):
        self.win_handle = window_handle

    def set_width(self, width):
        self.win_handle.Width = width

    def close(self):
        self.win_handle.Close()

    def hide(self):
        self.win_handle.Hide()


output_window = PyRevitConsoleWindow(_calling_scope_variable('__window__'))