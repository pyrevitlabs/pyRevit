class APIObjectWrapper:
    def __init__(self, rvt_obj):
        self._rvt_obj = rvt_obj

    def __repr__(self):
        return '<db.{} % {}>'.format(self.__class__.__name__, unicode(self._rvt_obj.ToString()))

    def unwrap(self):
        return self._rvt_obj


class ElementWrapper(APIObjectWrapper):
    def __init__(self, rvt_obj):
        APIObjectWrapper.__init__(self, rvt_obj)
        self.id = self._rvt_obj.Id.IntegerValue
        self.uniq_id = self._rvt_obj.UniqueId

    def __repr__(self):
        return APIObjectWrapper.__repr__(self).replace('>', ' id:{}>'.format(self.id))

    @classmethod
    def wrap(cls, rvt_element_list):
        return [cls(x) for x in rvt_element_list]
