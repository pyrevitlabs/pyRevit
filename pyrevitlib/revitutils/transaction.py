from revitutils import doc
from pyrevit.coreutils.logger import get_logger

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import Transaction, TransactionGroup


logger = get_logger(__name__)


DEFAULT_TRANSACTION_NAME = 'pyRevit Transaction'


class Action:
    def __init__(self, name=None):
        self.transaction = Transaction(doc, name if name else DEFAULT_TRANSACTION_NAME)

    def __enter__(self):
        self.transaction.Start()
        return self.transaction

    def __exit__(self, exception, exception_value, traceback):
        if exception:
            self.transaction.RollBack()
            logger.error('Error in Transactio Context: has rolled back.')
            logger.error('{}:{}'.format(exception, exception_value))
            raise exception(exception_value, '')
        else:
            try:
                self.transaction.Commit()
            except Exception as errmsg:
                self.transaction.RollBack()
                logger.error('Error in Transactio Commit: has rolled back.')
                logger.error('Error: {}'.format(errmsg))
                raise

    @staticmethod
    def carryout(name):
        from functools import wraps

        def wrap(f):
            @wraps(f)
            def wrapped_f(*args, **kwargs):
                with Action(name):
                    return_value = f(*args, **kwargs)
                return return_value
            return wrapped_f
        return wrap


class ActionGroup:
    def __init__(self, name=None, assimilate=True):
        self.transaction_group = TransactionGroup(doc, name if name else DEFAULT_TRANSACTION_NAME)
        self.assimilate = assimilate

    def __enter__(self):
        self.transaction_group.Start()
        return self.transaction_group

    def __exit__(self, exception, exception_value, traceback):
        if exception:
            self.transaction_group.RollBack()
            logger.error('Error in TransactionGroup Context: has rolled back.')
            logger.error('{}:{}'.format(exception, exception_value))
        else:
            try:
                if self.assimilate:
                    self.transaction_group.Assimilate()
                else:
                    self.transaction_group.Commit()
            except Exception as errmsg:
                self.transaction_group.RollBack()
                logger.error('Error in TransactionGroup Commit: has rolled back.')
                logger.error('Error: {}'.format(errmsg))
