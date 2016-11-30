__window__.Close()
import clr
import sys, os
folder = os.path.dirname( __file__ )

clr.AddReference('PresentationCore')
clr.AddReferenceByPartialName("PresentationFramework")
clr.AddReference('IronPython.Wpf')
from System.Windows import Application, Window
import wpf
# clr.AddReference('Microsoft.Dynamic')
# clr.AddReference('Microsoft.Scripting')
# clr.AddReference('System')
# clr.AddReference('IronPython')
# clr.AddReference('IronPython.Modules')
# clr.ImportExtensions(IronPython.Wpf)
# from System import Uri, UriKind
# from IronPython.Modules import Wpf as wpf


class AboutWindow(Window):
	def __init__(selfAbout, file):
		wpf.LoadComponent( selfAbout, os.path.join( folder, '__WIP__wpfTest__AboutWindow.xaml' ) )

class MyWindow(Window):
	def __init__(self):
		wpf.LoadComponent( self, os.path.join( folder, '__WIP__wpfTest__IronPythonWPF.xaml' ))

	def MenuItem_Click(self, sender, e):
		form = AboutWindow()
		form.ShowDialog()

if __name__ == '__main__':
	# Application().Run( MyWindow() )
	MyWindow().ShowDialog()
