import os.path as op

from pyrevit import PyRevitException
from pyrevit import framework
from pyrevit.revit import DB, UI
from pyrevit.coreutils.logger import get_logger

from Autodesk.Revit.DB import Element


logger = get_logger(__name__)


DEFAULT_TRANSACTION_NAME = 'pyRevit Transaction'


class ElementWrapper(object):
    def __init__(self, element):
        if isinstance(element, DB.Element):
            self._wrapped_element = element
        else:
            raise PyRevitException('Can not wrap object that are not '
                                   'derived from Element.')

    def __repr__(self):
        return '<pyrevit.revit.db.{} % {} id:{}>' \
                    .format(self.__class__.__name__,
                            self._wrapped_element.ToString(),
                            self._wrapped_element.Id)

    def unwrap(self):
        return self._wrapped_element

    @property
    def assoc_doc(self):
        return self._wrapped_element.Document

    @property
    def name(self):
        # have to use the imported Element otherwise
        # AttributeError occurs
        return Element.Name.GetValue(self._wrapped_element)

    @property
    def id(self):
        return self._wrapped_element.Id

    @property
    def unique_id(self):
        return self._wrapped_element.UniqueId

    @property
    def workset_id(self):
        return self._wrapped_element.WorksetId

    @property
    def mark(self):
        mparam = self._wrapped_element.LookupParameter('Mark')
        return mparam.AsString() if mparam else ''

    @property
    def location(self):
        return (self.x, self.y, self.z)

    @property
    def x(self):
        return self._wrapped_element.Location.Point.X

    @property
    def y(self):
        return self._wrapped_element.Location.Point.Y

    @property
    def z(self):
        return self._wrapped_element.Location.Point.Z

    def get_param(self, param_name):
        return self._wrapped_element.LookupParameter(param_name)


class CurrentElementSelection:
    def __init__(self):
        self.elements = \
            [__activedoc__.GetElement(el_id)
             for el_id in __activeuidoc__.Selection.GetElementIds()]

    def __len__(self):
        return len(self.elements)

    def __iter__(self):
        return iter(self.elements)

    @staticmethod
    def _get_element_ids(mixed_list):
        element_id_list = []

        if not isinstance(mixed_list, list):
            mixed_list = [mixed_list]

        for el in mixed_list:
            if isinstance(el, DB.ElementId):
                element_id_list.append(el)
            else:
                element_id_list.append(el.Id)

        return element_id_list

    @property
    def is_empty(self):
        return len(self.elements) == 0

    @property
    def element_ids(self):
        return [el.Id for el in self.elements]

    @property
    def first(self):
        if self.elements:
            return self.elements[0]

    @property
    def last(self):
        if self.elements:
            return self.elements[len(self)-1]

    def set_to(self, element_list):
        __activeuidoc__.Selection.SetElementIds(
            framework.List[ElementId](
                self._get_element_ids(element_list)
            )
        )
        __activeuidoc__.RefreshActiveView()

    def append(self, element_list):
        new_elids = self._get_element_ids(element_list)
        new_elids.extend(self.element_ids)
        __activeuidoc__.Selection.SetElementIds(
            framework.List[ElementId](new_elids)
        )
        self.elements = \
            [__activedoc__.GetElement(el_id) for el_id in new_elids]


class CurrentProjectInfo:
    def __init__(self):
        if not __activedoc__.IsFamilyDocument:
            self._info = __activedoc__.ProjectInformation
            self.name = self._info.Name
        self.location = __activedoc__.PathName
        self.filename = op.splitext(op.basename(__activedoc__.PathName))[0]


class Transaction():
    """
    Simplifies transactions by applying ``Transaction.Start()`` and
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
                 clear_after_rollback=False,
                 show_error_dialog=False):
        self._rvtxn = \
            DB.Transaction(__activedoc__,
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
    def __init__(self, name=None, assimilate=True):
        self._rvtxn_grp = \
            DB.TransactionGroup(__activedoc__,
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


def _pick_obj(self, obj_type, pick_message, multiple=False, world=False):
    refs = []

    try:
        logger.debug('Picking elements: '
                     '{} pick_message: '
                     '{} multiple: '
                     '{} world: '
                     '{}'.format(obj_type,
                                 pick_message,
                                 multiple, world))
        if multiple:
            refs = \
                list(__activeuidoc__.Selection.PickObjects(obj_type,
                                                           pick_message))
        else:
            refs = []
            refs.append(__activeuidoc__.Selection.PickObject(obj_type,
                                                             pick_message))

        if not refs:
            logger.debug('Nothing picked by user...Returning None')
            return None

        logger.debug('Picked elements are: {}'.format(refs))

        if obj_type == UI.Selection.ObjectType.Element:
            return_values = [__activedoc__.GetElement(ref) for ref in refs]
        elif obj_type == UI.Selection.ObjectType.PointOnElement:
            if world:
                return_values = [ref.GlobalPoint for ref in refs]
            else:
                return_values = [ref.UVPoint for ref in refs]
        else:
            return_values = \
                [__activedoc__.GetElement(ref)
                    .GetGeometryObjectFromReference(ref)
                 for ref in refs]

        logger.debug('Processed return elements are: {}'.format(return_values))

        if type(return_values) is list:
            if len(return_values) > 1:
                return return_values
            elif len(return_values) == 1:
                return return_values[0]
        else:
            logger.error('Error processing picked elements. '
                         'return_values should be a list.')
    except Exception:
        return None


def pick_element(self, pick_message=''):
    return self._pick_obj(UI.Selection.ObjectType.Element,
                          pick_message)


def pick_elementpoint(self, pick_message='', world=False):
    return self._pick_obj(UI.Selection.ObjectType.PointOnElement,
                          pick_message,
                          world=world)


def pick_edge(self, pick_message=''):
    return self._pick_obj(UI.Selection.ObjectType.Edge,
                          pick_message)


def pick_face(self, pick_message=''):
    return self._pick_obj(UI.Selection.ObjectType.Face,
                          pick_message)


def pick_linked(self, pick_message=''):
    return self._pick_obj(UI.Selection.ObjectType.LinkedElement,
                          pick_message)


def pick_elements(self, pick_message=''):
    return self._pick_obj(UI.Selection.ObjectType.Element,
                          pick_message,
                          multiple=True)


def pick_elementpoints(self, pick_message='', world=False):
    return self._pick_obj(UI.Selection.ObjectType.PointOnElement,
                          pick_message,
                          multiple=True, world=world)


def pick_edges(self, pick_message=''):
    return self._pick_obj(UI.Selection.ObjectType.Edge,
                          pick_message,
                          multiple=True)


def pick_faces(self, pick_message=''):
    return self._pick_obj(UI.Selection.ObjectType.Face,
                          pick_message,
                          multiple=True)


def pick_linkeds(self, pick_message=''):
    return self._pick_obj(UI.Selection.ObjectType.LinkedElement,
                          pick_message,
                          multiple=True)


def pick_point(self, pick_message=''):
    try:
        return __activeuidoc__.Selection.PickPoint(pick_message)
    except Exception:
            return None


def carryout(name):
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
            with Transaction(name):
                return_value = f(*args, **kwargs)
            return return_value
        return wrapped_f
    return wrap


def get_projectinfo():
    return CurrentProjectInfo()


def get_activeview():
    return __activeuidoc__.ActiveView


def get_selection():
    return CurrentElementSelection()
