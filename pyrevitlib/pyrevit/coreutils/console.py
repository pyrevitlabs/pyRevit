import clr

from pyrevit import EXEC_PARAMS
from pyrevit.coreutils import rvtprotocol
from pyrevit.coreutils import prepare_html_str

clr.AddReferenceByPartialName('System.Windows.Forms')
clr.AddReferenceByPartialName('System.Drawing')

# noinspection PyUnresolvedReferences
import System.Drawing
# noinspection PyUnresolvedReferences
import System.Windows


class PyRevitConsoleWindow:
    """Wrapper to interact with the output console window."""

    def __init__(self, window_handle):
        """Sets up the wrapper from the input dot net window handler"""
        self.__winhandle__ = window_handle
        self.__winhandle__.Width = 1100
        self.__winhandle__.UrlHandler = self.handle_protocol_url
        # self.__winhandle__.Show()

    def set_title(self, new_title):
        self.__winhandle__.Text = new_title

    def set_width(self, width):
        self.__winhandle__.Width = width

    def set_height(self, height):
        self.__winhandle__.Height = height

    def set_font(self, font_family_name, font_size):
        # noinspection PyUnresolvedReferences
        self.__winhandle__.txtStdOut.Font = System.Drawing.Font(font_family_name, font_size,
                                                                System.Drawing.FontStyle.Regular,
                                                                System.Drawing.GraphicsUnit.Point)

    def resize(self, width, height):
        self.set_width(width)
        self.set_height(height)

    def get_title(self):
        return self.__winhandle__.Text

    def get_width(self):
        return self.__winhandle__.Width

    def get_height(self):
        return self.__winhandle__.Height

    # user is not supposed to completely close the window but can always hide it.
    # def close(self):
    #     self.__winhandle__.Close()

    def hide(self):
        self.__winhandle__.Hide()

    def show(self):
        self.__winhandle__.Show()

    @staticmethod
    def handle_protocol_url(url):
        try:
            if rvtprotocol.PROTOCOL_NAME in url:
                cleaned_url = url.split(rvtprotocol.PROTOCOL_NAME)[1]
                # cleanup / and change single quotes back to double quotes
                cleaned_url = cleaned_url.replace('/', '').replace('\'','\"')
                rvtprotocol.process_url(cleaned_url)
        except Exception as exec_err:
            logger.error('Error handling link | {}'.format(exec_err))

    @staticmethod
    def linkify(*args):
        return prepare_html_str(rvtprotocol.make_url(args))

# __window__ used to be added to local scope by pyRevitLoader.dll, thus it needed to be extracted from caller scope
# pyRevitLoader.dll has been modified to add __window__ to globals. This snippet is for backup only
# from .coreutils import inspect_calling_scope_local_var
# win_handler = pyrevit.coreutils.inspect_calling_scope_local_var('__window__')
# if win_handler:
#     output_window = PyRevitConsoleWindow(win_handler)

# creates an instance of PyRevitConsoleWindow with the recovered __window__ handler.
output_window = PyRevitConsoleWindow(EXEC_PARAMS.window_handle)
