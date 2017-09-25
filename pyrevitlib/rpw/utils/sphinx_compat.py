import sys
import imp

from rpw.utils.logger import logger


class MockObject(object):
    """
    This gets passed back as an object when an import fails but is listed
    in dotnet_modules. This objects can have attributes retrieved, be
    iterated and called to allow for code to run without errors.
    This is used only when clr import fail, meaning code is being executed
    outside of Revit (sphinx)
    """
    # Defines for custom override for objects where the type is important
    # This is needed for example, so forms won't inherit form MockObject
    # which breaks sphinx autodoc
    MOCK_OVERRIDE = {'System.Windows.Window': object,
                     'Controls.Label': object,
                     'Controls.Button': object,
                     'Controls.TextBox': object,
                     'Controls.CheckBox': object,
                     'Controls.ComboBox': object,
                     'Controls.Separator': object,
                     }

    def __init__(self, *args, **kwargs):
        self.fullname = kwargs.get('fullname', '<Unamed Import>')

    def __getattr__(self, attr):
        logger.debug("Getting Atts:{} from {}')".format(attr, self.fullname))
        path_and_attr = '.'.join([self.fullname, attr])
        # print(path_and_attr)
        if path_and_attr in MockObject.MOCK_OVERRIDE:
            return MockObject.MOCK_OVERRIDE[path_and_attr]
        return MockObject(fullname=attr)

    def __iter__(self):
        yield iter(self)

    def AddReference(self, namespace):
        logger.debug("Mock.clr.AddReference('{}')".format(namespace))

    def __call__(self, *args, **kwargs):
        return MockObject(*args, **kwargs)

    def __repr__(self):
        return self.fullname

    def __str__(self):
        return self.fullname


class MockImporter(object):
    # https://github.com/gtalarico/revitpythonwrapper/issues/3
    # http://dangerontheranger.blogspot.com/2012/07/how-to-use-sysmetapath-with-python.html
    # http://blog.dowski.com/2008/07/31/customizing-the-python-import-system/

    dotnet_modules = ['clr',
                      'Autodesk',
                      'RevitServices',
                      'IronPython',
                      'System',
                      'wpf',
                      'Rhino',
                      ]

    def find_module(self, fullname, path=None):
        logger.debug('Loading : {}'.format(fullname))
        for module in self.dotnet_modules:
            if fullname.startswith(module):
                return self
        return None

    def load_module(self, fullname):
        """This method is called by Python if CustomImporter.find_module
           does not return None. fullname is the fully-qualified name
           of the module/package that was requested."""
        if fullname in sys.modules:
            return sys.modules[fullname]
        else:
            logger.debug('Importing Mock Module: {}'.format(fullname))
            # mod = imp.new_module(fullname)
            # import pdb; pdb.set_trace()
            mod = MockObject(fullname=fullname)
            mod.__loader__ = self
            mod.__file__ = fullname
            mod.__path__ = [fullname]
            mod.__name__ = fullname
            sys.modules[fullname] = mod
            return mod  # This gives errors
