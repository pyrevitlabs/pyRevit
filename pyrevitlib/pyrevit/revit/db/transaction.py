"""Revit transactions facility."""
from pyrevit import HOST_APP, DOCS, DB
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit.revit.db import failure


__all__ = ('carryout',
           'Transaction', 'DryTransaction', 'TransactionGroup')


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


DEFAULT_TRANSACTION_NAME = 'pyRevit Transaction'


class Transaction():
    """Adds a context manager around Revit Transaction object.

    Runs `Transaction.Start()` and `Transaction.Commit()`
    before and after the context.
    Automatically rolls back if exception is raised.

    ```python
        with Transaction('Move Wall'):
            wall.DoSomething()

        with Transaction('Move Wall', doc, clear_after_rollback=False, show_error_dialog=False, swallow_errors=False, log_errors=True, nested=False) as action:
            wall.DoSomething()
            assert action.status == ActionStatus.Started  # True
            assert action.status == ActionStatus.Committed    # True
        ```
    """
    def __init__(self, name=None,
                 doc=None,
                 clear_after_rollback=False,
                 show_error_dialog=False,
                 swallow_errors=False,
                 log_errors=True,
                 nested=False):
        doc = doc or DOCS.doc
        # create nested transaction if one is already open
        if doc.IsModifiable or nested:
            self._rvtxn = \
                DB.SubTransaction(doc)
        else:
            self._rvtxn = \
                DB.Transaction(doc, name if name else DEFAULT_TRANSACTION_NAME)
            self._fhndlr_ops = self._rvtxn.GetFailureHandlingOptions()
            self._fhndlr_ops = \
                self._fhndlr_ops.SetClearAfterRollback(clear_after_rollback)
            self._fhndlr_ops = \
                self._fhndlr_ops.SetForcedModalHandling(show_error_dialog)
            if swallow_errors:
                self._fhndlr_ops = \
                    self._fhndlr_ops.SetFailuresPreprocessor(
                        failure.FailureSwallower()
                        )
            self._rvtxn.SetFailureHandlingOptions(self._fhndlr_ops)
        self._logerror = log_errors

    def __enter__(self):
        self._rvtxn.Start()
        return self

    def __exit__(self, exception, exception_value, traceback):
        if exception:
            self._rvtxn.RollBack()
            if self._logerror:
                mlogger.error('Error in Transaction Context. '
                              'Rolling back changes. | %s:%s',
                              exception, exception_value)
        else:
            try:
                self._rvtxn.Commit()
            except Exception as errmsg:
                self._rvtxn.RollBack()
                if self._logerror:
                    mlogger.error('Error in Transaction Commit. '
                                  'Rolling back changes. | %s', errmsg)
        self._rvtxn.Dispose()

    @property
    def name(self):
        if hasattr(self._rvtxn, 'GetName'):
            return self._rvtxn.GetName()

    @name.setter
    def name(self, new_name):
        if hasattr(self._rvtxn, 'SetName'):
            return self._rvtxn.SetName(new_name)

    @property
    def status(self):
        return self._rvtxn.GetStatus()

    def has_started(self):
        return self._rvtxn.HasStarted()

    def has_ended(self):
        return self._rvtxn.HasEnded()


class DryTransaction(Transaction):
    """Wrapper to a transaction that doesn't commit anything (dry-run)."""
    def __exit__(self, exception, exception_value, traceback):
        self._rvtxn.RollBack()
        self._rvtxn.Dispose()


class TransactionGroup():
    """Transactions group with context manager."""
    def __init__(self, name=None, doc=None, assimilate=True, log_errors=True):
        self._rvtxn_grp = \
            DB.TransactionGroup(doc or DOCS.doc,
                                name if name else DEFAULT_TRANSACTION_NAME)
        self.assimilate = assimilate
        self._logerror = log_errors

    def __enter__(self):
        self._rvtxn_grp.Start()
        return self

    def __exit__(self, exception, exception_value, traceback):
        if exception:
            self._rvtxn_grp.RollBack()
            if self._logerror:
                mlogger.error('Error in TransactionGroup Context. '
                              'Rolling back changes. | %s:%s',
                              exception, exception_value)
        else:
            try:
                if self.assimilate:
                    self._rvtxn_grp.Assimilate()
                else:
                    self._rvtxn_grp.Commit()
            except Exception as errmsg:
                self._rvtxn_grp.RollBack()
                if self._logerror:
                    mlogger.error('Error in TransactionGroup Commit. '
                                  'Rolling back changes. | %s', errmsg)
        self._rvtxn_grp.Dispose()

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
    """Transaction Decorator.

    Decorate any function with ``@doc.carryout('Txn name')``
    and the funciton will run within an Transaction context.

    Args:
        name (str): Name of the Transaction
        doc (Document): Revit document

    ```python
    @doc.carryout('Do Something')
    def set_some_parameter(wall, value):
        wall.parameters['Comments'].value = value
    
    
    set_some_parameter(wall, value)
    ```
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
