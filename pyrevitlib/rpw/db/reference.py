"""
Reference Wrappers

>>> pick = rpw.ui.Pick()
>>> references = pick.pick_element(multiple=True)
>>> references
[<rpw:Reference>, <rpw:Reference>]
>>> references[0].as_global_pt
<rpw:XYZ>

Linked Element

>>> reference = pick.pick_linked_element()
>>> element = reference.get_element()

"""

import rpw
from rpw import revit, DB
from rpw.db.element import Element
from rpw.db.xyz import XYZ
from rpw.utils.logger import logger
# from rpw.db.builtins import BipEnum


class Reference(Element):
    """
    `DB.Reference` Wrapper
    Inherits from :any:`Element`

    >>>

    Attribute:
        _revit_object (DB.Reference): Wrapped ``DB.Reference``
        doc (Document): Element Document
    """

    _revit_object_class = DB.Reference

    def __init__(self, reference, linked=False):
        if not linked:
            doc = revit.doc
        else:
            link_instance = revit.doc.GetElement(reference.ElementId)
            doc = link_instance.GetLinkDocument()

        super(Reference, self).__init__(reference, doc=doc)
        self.doc = doc
        self.linked = linked

    def __repr__(self):
        return super(Reference, self).__repr__(data={'id': self.id})

    @property
    def as_global_pt(self):
        """ Returns ``GlobalPoint`` property of Reference """
        pt = self._revit_object.GlobalPoint
        if pt:
            return XYZ(pt)

    @property
    def as_uv_pt(self):
        """ Returns ``UVPoint`` property of Reference - Face references only """
        pt = self._revit_object.UVPoint
        if pt:
            # TODO XYZ needs to handle XYZ
            return pt
            # return XYZ(pt)

    @property
    def id(self):
        """ ElementId of Reference """
        return self._revit_object.ElementId if not self.linked else self._revit_object.LinkedElementId

    def get_element(self, wrapped=True):
        """ Element of Reference """
        element = self.doc.GetElement(self.id)
        return element if not wrapped else Element(element)

    def get_geometry(self):
        """ GeometryObject from Reference """
        ref = self._revit_object
        return self.doc.GetElement(ref).GetGeometryObjectFromReference(ref)
