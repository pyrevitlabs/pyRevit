from unittest import TestCase

from pyrevit import HOST_APP
test_doc = HOST_APP.uiapp.ActiveUIDocument.Document
test_uidoc = HOST_APP.uiapp.ActiveUIDocument
test_alldocs = HOST_APP.uiapp.Application.Documents
test_projectinfo = test_doc.ProjectInformation


class TestRevitUtilsImports(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_docAccess(self):
        """revitutils document access test"""
        try:
            from revitutils import doc, uidoc, all_docs
        except Exception as e:
            raise e

    def test_projectInfo(self):
        """revitutils project info test"""
        try:
            from revitutils import project
        except Exception as e:
            raise e

    def test_selection(self):
        """revitutils current user selection test"""
        try:
            from revitutils import selection
        except Exception as e:
            raise e

    def test_transaction(self):
        """revitutils transaction test"""
        try:
            from revitutils import Action
        except Exception as e:
            raise e

    def test_transcationGroup(self):
        """revitutils transaction group test"""
        try:
            from revitutils import ActionGroup
        except Exception as e:
            raise e
