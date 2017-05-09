# noinspection PyUnresolvedReferences
from rpw import DB, BaseObjectWrapper, doc


class ProjectInfo(BaseObjectWrapper):
    def __init__(self, api_obj):
        super(ProjectInfo, self).__init__(api_obj,
                                          enforce_type=DB.ProjectInfo)
        self.name = self._wrapped_object.Name
        self.number = self._wrapped_object.Number
        self.org_desc = self._wrapped_object.OrganizationDescription
        self.org_name = self._wrapped_object.OrganizationName
        self.status = self._wrapped_object.Status
        self.building_name = self._wrapped_object.BuildingName
        self.client_name = self._wrapped_object.ClientName
        self.issue_date = self._wrapped_object.IssueDate
        self.location = doc.PathName


projectinfo = ProjectInfo(doc.ProjectInformation)
