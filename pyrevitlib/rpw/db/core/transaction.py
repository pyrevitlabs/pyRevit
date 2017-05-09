# noinspection PyUnresolvedReferences
from rpw import DB, doc, get_logger, BaseObjectWrapper


logger = get_logger(__name__)


DEFAULT_ACTION_NAME = 'rpw action'
DEFAULT_ACTION_GROUP_NAME = 'rpw action group'


class TransactionStatus:
    # initial value, the action has not started yet
    Uninitialized = DB.TransactionStatus.Uninitialized
    # action has begun (til committed or rolled back)
    Started = DB.TransactionStatus.Started
    # rolled back (aborted)
    RolledBack = DB.TransactionStatus.RolledBack
    # simply committed
    Committed = DB.TransactionStatus.Committed
    # returned from error handling that took over
    Pending = DB.TransactionStatus.Pending
    # error while committing or rolling back
    Error = DB.TransactionStatus.Error

    def __init__(self):
        pass

    @staticmethod
    def from_trans_stat(rvt_trans_stat):
        for stat_k, stat_v in TransactionStatus.__dict__.items():
            if stat_v == rvt_trans_stat:
                return stat_v


class Transaction(BaseObjectWrapper):
    """
    Simplifies transactions by applying ``DB.Transaction.Start()`` and
    ``DB.Transaction.Commit()`` before and after the context.
    Automatically rolls back if exception is raised.

    >>> with Transaction('Move Wall'):
    >>>     # some action

    >>> with Transaction('Move Wall') as action:
    >>>     # some action
    >>>     assert action.status == TransactionStatus.Started  # True
    >>> assert action.status == TransactionStatus.Committed    # True

    """

    def __init__(self, name=None,
                 clear_after_rollback=False, show_error_dialog=False):
        db_transaction = \
            DB.Transaction(doc, name if name else DEFAULT_ACTION_NAME)

        super(Transaction, self).__init__(db_transaction,
                                     enforce_type=DB.Transaction)

        self._fail_hndlr_ops = self._wrapped_object.GetFailureHandlingOptions()
        self._fail_hndlr_ops.SetClearAfterRollback(clear_after_rollback)
        self._fail_hndlr_ops.SetForcedModalHandling(show_error_dialog)
        self._wrapped_object.SetFailureHandlingOptions(self._fail_hndlr_ops)

    def __repr__(self, data=None):
        return super(Transaction, self).__repr__(data={'status': self.status})

    def __enter__(self):
        self._wrapped_object.Start()
        return self

    def __exit__(self, exception, exception_value, traceback):
        if exception:
            self._wrapped_object.RollBack()
            logger.error('Error in Transaction Context. Rolling back changes. '
                         '| {}:{}'.format(exception, exception_value))
        else:
            try:
                self._wrapped_object.Commit()
            except Exception as errmsg:
                self._wrapped_object.RollBack()
                logger.error('Error in Transaction Commit. Rolling back changes. '
                             '| {}'.format(errmsg))

    @property
    def name(self):
        return self._wrapped_object.GetName()

    @name.setter
    def name(self, new_name):
        self._wrapped_object.SetName(new_name)

    @property
    def status(self):
        return TransactionStatus.from_trans_stat(self._wrapped_object.GetStatus())

    @staticmethod
    def carryout(name):
        """ Transaction Decorator

        Decorate any function with ``@Transaction.carryout('Transaction Name')``
        and the funciton will run within an Transaction context.

        Args:
            name (str): Name of the Transaction

        Example:
            >>> @Transaction.carryout('Do Something')
            >>> def set_some_parameter(wall, value):
            >>>     wall.parameters['Comments'].value = value

        """

        from functools import wraps

        def wrap(f):
            @wraps(f)
            def wrapped_f(*args, **kwargs):
                with Transaction(name):
                    return_value = f(*args, **kwargs)
                return return_value
            return wrapped_f
        return wrap

    def has_started(self):
        return self._wrapped_object.HasStarted()

    def has_ended(self):
        return self._wrapped_object.HasEnded()


class DryTransaction(Transaction):
    def __exit__(self, exception, exception_value, traceback):
        self._wrapped_object.RollBack()


class TransactionGroup(BaseObjectWrapper):
    def __init__(self, name=None, assimilate=True):
        db_transaction_group = \
            DB.TransactionGroup(doc,
                                name if name else DEFAULT_ACTION_GROUP_NAME)

        super(TransactionGroup, self).__init__(db_transaction_group,
                                          enforce_type=DB.TransactionGroup)

        self.assimilate = assimilate
        self._wrapped_object = None

    def __enter__(self):
        self._wrapped_object.Start()
        return self

    def __exit__(self, exception, exception_value, traceback):
        if exception:
            self._wrapped_object.RollBack()
            logger.error('Error in DB.TransactionGroup Context: '
                         'has rolled back.')
            logger.error('{}:{}'.format(exception, exception_value))
        else:
            try:
                if self.assimilate:
                    self._wrapped_object.Assimilate()
                else:
                    self._wrapped_object.Commit()
            except Exception as errmsg:
                self._wrapped_object.RollBack()
                logger.error('Error in DB.TransactionGroup Commit: '
                             'has rolled back.')
                logger.error('Error: {}'.format(errmsg))

    @property
    def name(self):
        return self._wrapped_object.GetName()

    @name.setter
    def name(self, new_name):
        self._wrapped_object.SetName(new_name)

    @property
    def status(self):
        return TransactionStatus.from_trans_stat(self._wrapped_object.GetStatus())

    def has_started(self):
        return self._wrapped_object.HasStarted()

    def has_ended(self):
        return self._wrapped_object.HasEnded()
