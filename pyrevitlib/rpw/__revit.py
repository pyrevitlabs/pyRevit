"""
The main rpw namespace and rpw.revit provide you with most of the imports will
need.

>>> from rpw import revit, db, ui
>>> db.Element(SomeElement)
>>> ui.Selection()
>>> revit.doc
>>> revit.uidoc.ActiveView


Revit Namespaces are also available:

>>> from rpw import DB, UI
>>> DB.ElementId(00000)
>>> UI.TaskDialog

In summary, if you use rpw, this could potentially be the only import line
you would need:

>>> from rpw import revit, db, ui, DB, UI

"""  #
import rpw
from rpw.utils.dotnet import clr, Process
from rpw.utils.logger import logger
from rpw.base import BaseObject


class Revit(BaseObject):
    """
    Revit Application Wrapper

    Note:
        The module path for the Revit Wrapper and its namespaces is ``rpw.__revit.Revit``.
        However, the ``Revit()`` is always instantiated on the initialization of rpw,
        and is stored along with the ``DB`` and ``UI`` namespaces in the
        root of rpw module.

        In other words, to use this wrapper all you need is to import
        ``from rpw import revit``

    >>> from rpw import revit
    >>> revit.doc
    <Autodesk.Revit.DB.Document>
    >>> revit.username
    gtalarico
    >>> revit.host
    'Dynamo'

    """

    class HOSTS():
        RPS = 'RPS'
        DYNAMO = 'Dynamo'

    def __init__(self):
        try:
            self.uiapp = __revit__
            self._host = Revit.HOSTS.RPS
        except NameError:
            try:
                # Try Getting handler from Dynamo RevitServices
                self.uiapp = self.find_dynamo_uiapp()
                self._host = Revit.HOSTS.DYNAMO
            except Exception as errmsg:
                logger.warning('Revit Application handle could not be found')

        try:
            # Add DB UI Import to globals so it can be imported by rpw
            clr.AddReference('RevitAPI')
            clr.AddReference('RevitAPIUI')
            from Autodesk.Revit import DB, UI
            globals().update({'DB': DB, 'UI': UI})
        except Exception:
            # Replace Globals with Mock Objects for Sphinx and ipy direct exec.
            logger.warning('RevitAPI References could not be added')
            from rpw.utils.sphinx_compat import MockObject
            globals().update({'DB': MockObject(fullname='Autodesk.Revit.DB'),
                              'UI': MockObject(fullname='Autodesk.Revit.DB')})
            self.uiapp = MockObject(fullname='Autodesk.Revit.UI.UIApplication')
            self._host = None

    def find_dynamo_uiapp(self):
        clr.AddReference("RevitServices")
        import RevitServices
        from RevitServices.Persistence import DocumentManager

        import sys
        sys.path.append(r'C:\Program Files (x86)\IronPython 2.7\Lib')
        return DocumentManager.Instance.CurrentUIApplication

    @property
    def host(self):
        """ Host is set based on how revit handle was found.

        Returns:
            Host (str): Revit Application Host ['RPS', 'Dynamo']
        """
        return self._host

    def open(self, path):
        """ Opens New Document """

    @property
    def doc(self):
        """ Returns: uiapp.ActiveUIDocument.Document """
        return getattr(self.uiapp.ActiveUIDocument, 'Document', None)

    @property
    def uidoc(self):
        """ Returns: uiapp.ActiveUIDocument """
        return getattr(self.uiapp, 'ActiveUIDocument', None)

    @property
    def active_view(self):
        """ Returns: uidoc.ActiveView """
        return rpw.db.Element(self.uidoc.ActiveView)

    @active_view.setter
    def active_view(self, view_reference):
        self.uidoc.ActiveView = view_reference

    @property
    def app(self):
        """ Returns: uidoc.Application """
        return self.uiapp.Application

    @property
    def docs(self):
        """ Returns: uidoc.Application.Documents """
        return [doc for doc in self.app.Documents]

    @property
    def username(self):
        """ Returns: uidoc.Application.Username """
        return self.uiapp.Application.Username

    @property
    def version(self):
        """ Returns: uidoc.Application.Username """
        return RevitVersion(self.uiapp)

    @property
    def process(self):
        """ Returns: Process.GetCurrentProcess() """
        return Process.GetCurrentProcess()

    @property
    def process_id(self):
        """ Returns: Process.GetCurrentProcess() """
        return self.process.Id

    @property
    def process_name(self):
        """ Returns: Process.GetCurrentProcess() """
        return self.process.ProcessName

    def __repr__(self):
        return '<{version} [{process}:{pid}]>'.format(version=self.version,
                                                      process=self.process_name,
                                                      pid=self.process_id)
    # Check what this is
    # @property
    # def process(self):
    #     clr.AddReferenceByPartialName('System.Windows.Forms')
    #     # noinspection PyUnresolvedReferences
    #     from System.Windows.Forms import Screen
    #     return Screen.FromHandle(Process.GetCurrentProcess().MainWindowHandle)


class RevitVersion():
    def __init__(self, uiapp):
        self.uiapp = uiapp

    @property
    def year(self):
        return self.uiapp.Application.VersionNumber

    @property
    def name(self):
        return self.uiapp.Application.VersionName

    @property
    def build(self):
        return self.uiapp.Application.VersionBuild

    def __lt__(self, other):
        """ Handle Version Comparison Logic"""
        raise NotImplemented

    def __gt__(self, other):
        """ Handle Version Comparison Logic"""
        raise NotImplemented

    def __repr__(self):
        return '<Version: {year}: {build}>'.format(year=self.name,
                                                   build=self.build)

    def __str__(self):
        return '{name}:{build}'.format(name=self.name, build=self.build)


revit = Revit()
