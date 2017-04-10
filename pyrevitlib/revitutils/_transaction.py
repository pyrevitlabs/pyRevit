from revitutils import doc
from pyrevit.coreutils.logger import get_logger

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import Transaction, TransactionGroup, TransactionStatus, FailureHandlingOptions


logger = get_logger(__name__)


DEFAULT_TRANSACTION_NAME = 'pyRevit Action'


class ActionStatus:
    Uninitialized = TransactionStatus.Uninitialized   # initial value, the action has not started yet
    Started = TransactionStatus.Started               # action has begun (til committed or rolled back)
    RolledBack = TransactionStatus.RolledBack         # rolled back (aborted)
    Committed = TransactionStatus.Committed           # simply committed
    Pending = TransactionStatus.Pending               # returned from error handling that took over
    Error = TransactionStatus.Error                   # error while committing or rolling back

    @staticmethod
    def from_rvt_trans_stat(rvt_trans_stat):
        for stat_k, stat_v in ActionStatus.__dict__.items():
            if stat_v == rvt_trans_stat:
                return stat_v


class Action:
    def __init__(self, name=None, clear_after_rollback=False, show_error_dialog=False):
        self._rvt_transaction = Transaction(doc, name if name else DEFAULT_TRANSACTION_NAME)
        self._fail_hndlr_ops = self._rvt_transaction.GetFailureHandlingOptions()
        self._fail_hndlr_ops.SetClearAfterRollback(clear_after_rollback)
        self._fail_hndlr_ops.SetForcedModalHandling(show_error_dialog)
        self._rvt_transaction.SetFailureHandlingOptions(self._fail_hndlr_ops)

    def __enter__(self):
        self._rvt_transaction.Start()
        return self

    def __exit__(self, exception, exception_value, traceback):
        if exception:
            self._rvt_transaction.RollBack()
            logger.error('Error in Action Context. Rolling back changes. | {}:{}'.format(exception,
                                                                                         exception_value))
        else:
            try:
                self._rvt_transaction.Commit()
            except Exception as errmsg:
                self._rvt_transaction.RollBack()
                logger.error('Error in Action Commit. Rolling back changes. | {}'.format(errmsg))

    @property
    def name(self):
        return self._rvt_transaction.GetName()

    @name.setter
    def name(self, new_name):
        return self._rvt_transaction.SetName(new_name)

    @property
    def status(self):
        return ActionStatus.from_rvt_trans_stat(self._rvt_transaction.GetStatus())

    @staticmethod
    def carryout(name):
        """ Action Decorator

        Decorate any function with ``@Action.carryout('Action Name')``
        and the funciton will run within an Action context.

        Args:
            name (str): Name of the Action

        >>> @Action.carryout('Do Something')
        >>> def set_some_parameter(wall, value):
        >>>     wall.parameters['Comments'].value = value
        >>>
        >>> set_some_parameter(wall, value)
        """
        from functools import wraps

        def wrap(f):
            @wraps(f)
            def wrapped_f(*args, **kwargs):
                with Action(name):
                    return_value = f(*args, **kwargs)
                return return_value
            return wrapped_f
        return wrap

    def has_started(self):
        return self._rvt_transaction.HasStarted()

    def has_ended(self):
        return self._rvt_transaction.HasEnded()


class DryAction(Action):
    def __exit__(self, exception, exception_value, traceback):
        self._rvt_transaction.RollBack()


class ActionGroup:
    def __init__(self, name=None, assimilate=True):
        self._rvt_transaction_group = TransactionGroup(doc, name if name else DEFAULT_TRANSACTION_NAME)
        self.assimilate = assimilate

    def __enter__(self):
        self._rvt_transaction_group.Start()
        return self

    def __exit__(self, exception, exception_value, traceback):
        if exception:
            self._rvt_transaction_group.RollBack()
            logger.error('Error in TransactionGroup Context: has rolled back.')
            logger.error('{}:{}'.format(exception, exception_value))
        else:
            try:
                if self.assimilate:
                    self._rvt_transaction_group.Assimilate()
                else:
                    self._rvt_transaction_group.Commit()
            except Exception as errmsg:
                self._rvt_transaction_group.RollBack()
                logger.error('Error in TransactionGroup Commit: has rolled back.')
                logger.error('Error: {}'.format(errmsg))

    @property
    def name(self):
        return self._rvt_transaction_group.GetName()

    @name.setter
    def name(self, new_name):
        return self._rvt_transaction_group.SetName(new_name)

    @property
    def status(self):
        return ActionStatus.from_rvt_trans_stat(self._rvt_transaction_group.GetStatus())


    def has_started(self):
        return self._rvt_transaction_group.HasStarted()

    def has_ended(self):
        return self._rvt_transaction_group.HasEnded()
