from unittest import TestCase


class TestRevitUtilsImports(TestCase):
    def test_docAccess(self):
        try:
            from revitutils import doc, uidoc, all_docs
        except Exception as e:
            raise e

    def test_projectInfo(self):
        try:
            from revitutils import project
        except Exception as e:
            raise e

    def test_selection(self):
        try:
            from revitutils import selection
        except Exception as e:
            raise e

    def test_transaction(self):
        try:
            from revitutils import Action
        except Exception as e:
            raise e

    def test_transcationGroup(self):
        try:
            from revitutils import ActionGroup
        except Exception as e:
            raise e
