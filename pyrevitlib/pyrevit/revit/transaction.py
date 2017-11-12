from pyrevit import HOST_APP, DB
from pyrevit.coreutils.logger import get_logger


logger = get_logger(__name__)


DEFAULT_TRANSACTION_NAME = 'pyRevit Transaction'


class Transaction():
    """Simplifies transactions by applying ``Transaction.Start()`` and
    ``Transaction.Commit()`` before and after the context.
    Automatically rolls back if exception is raised.

    >>> with Transaction('Move Wall'):
    >>>     wall.DoSomething()

    >>> with Transaction('Move Wall') as action:
    >>>     wall.DoSomething()
    >>>     assert action.status == ActionStatus.Started  # True
    >>> assert action.status == ActionStatus.Committed    # True
    """
    def __init__(self, name=None,
                 doc=None,
                 clear_after_rollback=False,
                 show_error_dialog=False):
        self._rvtxn = \
            DB.Transaction(doc or HOST_APP.doc,
                           name if name else DEFAULT_TRANSACTION_NAME)
        self._fail_hndlr_ops = self._rvtxn.GetFailureHandlingOptions()
        self._fail_hndlr_ops.SetClearAfterRollback(clear_after_rollback)
        self._fail_hndlr_ops.SetForcedModalHandling(show_error_dialog)
        self._rvtxn.SetFailureHandlingOptions(self._fail_hndlr_ops)

    def __enter__(self):
        self._rvtxn.Start()
        return self

    def __exit__(self, exception, exception_value, traceback):
        if exception:
            self._rvtxn.RollBack()
            logger.error('Error in Transaction Context. '
                         'Rolling back changes. | {}:{}'
                         .format(exception, exception_value))
        else:
            try:
                self._rvtxn.Commit()
            except Exception as errmsg:
                self._rvtxn.RollBack()
                logger.error('Error in Transaction Commit. '
                             'Rolling back changes. | {}'.format(errmsg))

    @property
    def name(self):
        return self._rvtxn.GetName()

    @name.setter
    def name(self, new_name):
        return self._rvtxn.SetName(new_name)

    @property
    def status(self):
        return self._rvtxn.GetStatus()

    def has_started(self):
        return self._rvtxn.HasStarted()

    def has_ended(self):
        return self._rvtxn.HasEnded()


class DryTransaction(Transaction):
    def __exit__(self, exception, exception_value, traceback):
        self._rvtxn.RollBack()


class TransactionGroup():
    def __init__(self, name=None, doc=None, assimilate=True):
        self._rvtxn_grp = \
            DB.TransactionGroup(doc or HOST_APP.doc,
                                name if name else DEFAULT_TRANSACTION_NAME)
        self.assimilate = assimilate

    def __enter__(self):
        self._rvtxn_grp.Start()
        return self

    def __exit__(self, exception, exception_value, traceback):
        if exception:
            self._rvtxn_grp.RollBack()
            logger.error('Error in TransactionGroup Context: has rolled back.')
            logger.error('{}:{}'.format(exception, exception_value))
        else:
            try:
                if self.assimilate:
                    self._rvtxn_grp.Assimilate()
                else:
                    self._rvtxn_grp.Commit()
            except Exception as errmsg:
                self._rvtxn_grp.RollBack()
                logger.error('Error in TransactionGroup Commit: rolled back.')
                logger.error('Error: {}'.format(errmsg))

    @property
    def name(self):
        return self._rvtxn_grp.GetName()

    @name.setter
    def name(self, new_name):
        return self._rvtxn_grp.SetName(new_name)

    @property
    def status(self):
        return self._rvtxn_grp.GetStatus()

    def has_started(self):
        return self._rvtxn_grp.HasStarted()

    def has_ended(self):
        return self._rvtxn_grp.HasEnded()


def carryout(name, doc=None):
    """Transaction Decorator

    Decorate any function with ``@doc.carryout('Txn name')``
    and the funciton will run within an Transaction context.

    Args:
        name (str): Name of the Transaction

    >>> @doc.carryout('Do Something')
    >>> def set_some_parameter(wall, value):
    >>>     wall.parameters['Comments'].value = value
    >>>
    >>> set_some_parameter(wall, value)
    """
    from functools import wraps

    def wrap(f):
        @wraps(f)
        def wrapped_f(*args, **kwargs):
            with Transaction(name, doc=doc):
                return_value = f(*args, **kwargs)
            return return_value
        return wrapped_f
    return wrap
