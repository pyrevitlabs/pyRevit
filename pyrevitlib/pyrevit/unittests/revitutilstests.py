from unittest import TestCase

from pyrevit import HOST_APP
test_doc = HOST_APP.uiapp.ActiveUIDocument.Document
test_uidoc = HOST_APP.uiapp.ActiveUIDocument
test_alldocs = HOST_APP.uiapp.Application.Documents
test_projectinfo = test_doc.ProjectInformation


class TestRevitUtilsImports(TestCase):
    def test_docAccess(self):
        """revitutils document access import test"""
        try:
            from revitutils import doc, uidoc, all_docs
        except Exception as e:
            raise e

    def test_projectInfo(self):
        """revitutils project info import test"""
        try:
            from revitutils import project
        except Exception as e:
            raise e

    def test_selection(self):
        """revitutils current user selection import test"""
        try:
            from revitutils import selection
        except Exception as e:
            raise e

    def test_transaction(self):
        """revitutils transaction import test"""
        try:
            from revitutils import Action
        except Exception as e:
            raise e

    def test_transcationGroup(self):
        """revitutils transaction group import test"""
        try:
            from revitutils import ActionGroup
        except Exception as e:
            raise e


class TestRevitUtilsSelection(TestCase):
    def setUp(self):
        pass

    def test_getSelection(self):
        """revitutils selection access test"""
        pass
