import datetime


RESULT_DICT = {0: 'Succeeded',
               1: 'SysExited', 2: 'ExecutionException', 3: 'CompileException',
               9: 'UnknownException'}

TIMESTAMP_FORMAT = '%Y/%m/%d %H:%M:%S:%f'


class UsageRecord:
    def __init__(self):
        self._src_dict = None
        self.date = self.time = self.username = ''
        self.revit = self.revitbuild = self.sessionid = self.pyrevit = ''
        self.debug = self.alternate = False
        self.commandname = self.commandbundle = self.commandextension = ''
        self.resultcode = 0
        self.commandresults = {}
        self.scriptpath = ''

    def __repr__(self):
        return '<UsageRecord {}>'.format(self.commandname)

    def __eq__(self, other):
        return hash(str(self.__dict__)) == hash(str(other.__dict__))

    def __hash__(self):
        return hash(str(self.__dict__))

    def __lt__(self, other):
        mydate = datetime.datetime.strptime('{} {}'.format(self.date, self.time), TIMESTAMP_FORMAT)
        otherdate = datetime.datetime.strptime('{} {}'.format(other.date, other.time), TIMESTAMP_FORMAT)
        return mydate < otherdate

    @property
    def result(self):
        return RESULT_DICT[self.resultcode]

    @property
    def original_record(self):
        return self._src_dict

    def has_term(self, search_term):
        for value in self._src_dict.values():
            if search_term in unicode(value).lower():
                return True

    def update(self, src_dict):
        self.__dict__.update(src_dict)
        self._src_dict = src_dict
