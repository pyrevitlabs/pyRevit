"""Module for managing tags metadata."""
#pylint: disable=E0401,C0111,W0603,C0103,W0703
from pyrevit.coreutils import logger
from pyrevit import revit

from pkgcommits import CommitPointTypes
from pkgcommits import CommitPoint, Commit, CommitHistory
import pkgcfg


mlogger = logger.get_logger(__name__)


class CommitedSheet(object):
    def __init__(self, view_sheet, commit_points):
        commit_cfg = pkgcfg.CommitConfigs()

        self._item = view_sheet
        self._chistory = CommitHistory(commit_points)
        self._read_commit_history(commit_cfg)

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

    def get_commit_at_point(self, commit_point):
        commit = self.commit_history.get_commit_at_point(commit_point)
        return commit or Commit.from_point(commit_point)

    def _read_commit_history(self, commit_cfg):
        # process package commits
        for commit_pt in [x for x in self.commit_history.commit_points
                          if x.cptype == CommitPointTypes.Package]:
            pkg_param = self.revit_sheet.LookupParameter(commit_pt.name)
            if pkg_param:
                ctype = commit_cfg.get_commit_type(pkg_param.AsString())
                # add commit to sheet commits
                if ctype:
                    try:
                        self.commit(commit_pt,
                                    commit_type=ctype,
                                    allow_endpoint_change=True)
                    except Exception as e:
                        mlogger.debug(
                            'Commit error on %s:%s at %s | %s',
                            self.number, self.name, commit_pt, type(e)
                            )

        # process revisions
        sheet_revids = \
            {x.IntegerValue for x in self.revit_sheet.GetAllRevisionIds()}
        add_sheet_revids = \
            {x.IntegerValue
             for x in self.revit_sheet.GetAdditionalRevisionIds()}
        readonly_sheet_revids = sheet_revids - add_sheet_revids

        default_rev_commit_type = CommitPointTypes.Revision.default_commit_type

        for commit_pt in [x for x in self.commit_history.commit_points
                          if x.cptype == CommitPointTypes.Revision]:
            for sheet_revid in sheet_revids:
                if commit_pt.target == sheet_revid:
                    readonly = sheet_revid in readonly_sheet_revids
                    try:
                        new_commit = self.commit(
                            commit_pt,
                            commit_type=default_rev_commit_type
                            )
                        new_commit.read_only = readonly
                    except Exception as e:
                        mlogger.debug(
                            'Commit error on %s:%s at %s | %s',
                            self.number, self.name, commit_pt, type(e)
                            )

    def update_commit_history(self):
        commit_cfg = pkgcfg.CommitConfigs()
        # process package commits
        for commit_pt in [x for x in self.commit_history.commit_points
                          if x.cptype == CommitPointTypes.Package]:
            pkg_param = self.revit_sheet.LookupParameter(commit_pt.name)
            if pkg_param:
                commit = self.get_commit_at_point(commit_pt)
                pkg_param.Set(commit_cfg.get_commit_value(commit.ctype))

        # process revisions
        sheet_revs = [revit.doc.GetElement(x)
                      for x in self.revit_sheet.GetAllRevisionIds()]
        for commit_pt in [x for x in self.commit_history.commit_points
                          if x.cptype == CommitPointTypes.Revision]:
            pass

    def commit(self, commit_point, commit_type, allow_endpoint_change=False):
        return self.commit_history.commit_at_point(
            commit_point,
            commit_type=commit_type,
            allow_endpoint_change=allow_endpoint_change
            )


def get_commit_points():
    commit_points = []
    # grab defined packages
    commit_points.extend([
        CommitPoint(cptype=CommitPointTypes.Package,
                    target=None,
                    idx=0,
                    name='Package 1'),
        CommitPoint(cptype=CommitPointTypes.Package,
                    target=None,
                    idx=1,
                    name='Package 2'),
        CommitPoint(cptype=CommitPointTypes.Package,
                    target=None,
                    idx=2,
                    name='Package 3'),
        CommitPoint(cptype=CommitPointTypes.Package,
                    target=None,
                    idx=3,
                    name='Package 4'),
        CommitPoint(cptype=CommitPointTypes.Package,
                    target=None,
                    idx=4,
                    name='Package 5'),
        CommitPoint(cptype=CommitPointTypes.Package,
                    target=None,
                    idx=5,
                    name='Package 6'),
        ])
    # grab revisions
    last_pkg_index = 5
    docrevs = revit.query.get_revisions()
    commit_points.extend([
        CommitPoint(cptype=CommitPointTypes.Revision,
                    target=x.Id.IntegerValue,
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
        cmt_sheet = CommitedSheet(sheet, commit_points)
        commited_sheets.append(cmt_sheet)

    return commited_sheets
