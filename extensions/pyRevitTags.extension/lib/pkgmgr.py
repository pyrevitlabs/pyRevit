"""Module for managing tags metadata."""
#pylint: disable=E0401,C0111,W0603,C0103
from pyrevit import PyRevitException
from pyrevit.coreutils import logger
from pyrevit import revit, DB
from pyrevit.revit import query
from pyrevit.revit import create

from pkgcommits import CommitTargets, CommitTypes
from pkgcommits import CommitPoint, Commit, CommitHistory
import pkgcfg


mlogger = logger.get_logger(__name__)


class CommitedSheet(object):
    def __init__(self, view_sheet):
        self._item = view_sheet
        self._chistory = CommitHistory()

    @property
    def revit_sheet(self):
        return self._item

    @property
    def name(self):
        return self.revit_sheet.Name

    @property
    def number(self):
        return self.revit_sheet.SheetNumber

    @property
    def commit_history(self):
        return self._chistory

    def read_commit_history(self, commit_points, commit_cfg):
        # process package commits
        for commit_pt in [x for x in commit_points
                          if x.cptype == CommitTargets.Package]:
            pkg_param = self.revit_sheet.LookupParameter(commit_pt.name)
            if pkg_param:
                ctype = commit_cfg.get_commit_type(pkg_param.AsString())
                # add commit to sheet commits
                if ctype:
                    self._chistory.commit_at_point(
                        commit_pt, commit_type=ctype
                        )
        # process revisions
        sheet_revs = [revit.doc.GetElement(x)
                      for x in self.revit_sheet.GetAllRevisionIds()]
        for commit_pt in [x for x in commit_points
                          if x.cptype == CommitTargets.Revision]:
            for sheet_rev in sheet_revs:
                if commit_pt.target.Id == sheet_rev.Id:
                    self._chistory.commit_at_point(
                        commit_pt, commit_type=CommitTypes.Revised
                    )

    def commit(self, commit_pt, commit_type):
        self._chistory.commit_at_point(commit_pt, commit_type=commit_type)


def get_commit_points():
    commit_points = []
    # grab defined packages
    commit_points.extend([
        CommitPoint(cptype=CommitTargets.Package,
                    target=None,
                    idx=0,
                    name='Package 1'),
        CommitPoint(cptype=CommitTargets.Package,
                    target=None,
                    idx=1,
                    name='Package 2'),
        CommitPoint(cptype=CommitTargets.Package,
                    target=None,
                    idx=2,
                    name='Package 3'),
        CommitPoint(cptype=CommitTargets.Package,
                    target=None,
                    idx=3,
                    name='Package 4'),
        ])
    # grab revisions
    last_pkg_index = 3
    docrevs = revit.query.get_revisions()
    commit_points.extend([
        CommitPoint(cptype=CommitTargets.Revision,
                    target=x,
                    idx=x.SequenceNumber + last_pkg_index,
                    name=x.Description)
        for x in docrevs
        ])
    return sorted(commit_points, key=lambda x: x.idx)


def get_commited_sheets():
    commit_points = get_commit_points()

    commited_sheets = []
    doc_sheets = revit.query.get_sheets(include_noappear=False)
    for sheet in doc_sheets:
        cmt_sheet = CommitedSheet(sheet)
        cmt_sheet.read_commit_history(commit_points, pkgcfg.CommitConfigs())
        commited_sheets.append(cmt_sheet)

    return commited_sheets
