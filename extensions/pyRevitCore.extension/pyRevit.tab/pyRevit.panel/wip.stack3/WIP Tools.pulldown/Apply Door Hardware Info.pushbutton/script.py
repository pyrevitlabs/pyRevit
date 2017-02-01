"""Shows pyRevit runtime debug logs."""

from scriptutils.userinput import WPFWindow

class ExtensionsWindow(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)

if __name__ == '__main__':
    ExtensionsWindow('DoorHardwareWindow.xaml').ShowDialog()
