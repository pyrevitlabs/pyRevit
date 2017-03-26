from unittest import TestCase


class TestDocumentAccess(TestCase):
    def test_action(self):
        try:
            from revitutils import doc, uidoc, all_docs
        except Exception as e:
            raise e


class TestProjectInfo(TestCase):
    def test_action(self):
        try:
            from revitutils import project
        except Exception as e:
            raise e


class TestSelection(TestCase):
    def test_action(self):
        try:
            from revitutils import selection
        except Exception as e:
            raise e


class TestTransaction(TestCase):
    def test_action(self):
        try:
            from revitutils import Action
        except Exception as e:
            raise e


class TestTransactionGroup(TestCase):
    def test_action(self):
        try:
            from revitutils import ActionGroup
        except Exception as e:
            raise e
