"""
Reference Wrappers

"""

# import rpw
# from rpw import revit, DB
# from rpw.db import Element
# from rpw.utils.logger import logger
# from rpw.db.builtins import BipEnum


# class Reference(Element):
#     """
#     `DB.Architecture.Room` Wrapper
#     Inherits from :any:`Element`
#
#     >>> room = rpw.Room(SomeRoom)
#     <RPW_Room: Office:122>
#     >>> room.name
#     'Office'
#     >>> room.number
#     '122'
#     >>> room.is_placed
#     True
#     >>> room.is_bounded
#     True
#
#     Attribute:
#         _revit_object (DB.Architecture.Room): Wrapped ``DB.Architecture.Room``
#     """
#
#     _revit_object_class = DB.Architecture.Room
#     _revit_object_category = DB.BuiltInCategory.OST_Rooms
#     _collector_params = {'of_category': _revit_object_category,
#                          'is_not_type': True}
#
#
#     def __repr__(self):
#         return super(Room, self).__repr__(data={'name': self.name,
#                                                 'number': self.number})

# def _pick(self, obj_type, msg='', multiple=False, world=None):
#     doc = self.uidoc.Document
#
#     if multiple:
#         refs = PickObjects(obj_type, msg)
#     else:
#         refs = PickObject(obj_type, msg)
#
#     refs = to_iterable(refs)
#
#     ref_dict = {}  # Return Value
#
#     if world:
#         try:
#             global_pts = [ref.GlobalPoint for ref in refs]
#         except AttributeError:
#             raise
#         else:
#             global_pts = global_pts if multiple else global_pts[0]
#             ref_dict['global_points'] = global_pts
#     if world is False:
#         try:
#             uv_pts = [ref.UVPoint for ref in refs]
#         except AttributeError:
#             raise
#         else:
#             uv_pts = uv_pts if multiple else uv_pts[0]
#             ref_dict['uv_points'] = uv_pts
#     try:
#         ref_dict['geometric_object'] = [doc.GetElement(ref).GetGeometryObjectFromReference(ref) for ref in refs]
#     except AttributeError:
#         raise
#
#     self.add(refs)
#     rpw.ui.Console()
#     return ref_dict
