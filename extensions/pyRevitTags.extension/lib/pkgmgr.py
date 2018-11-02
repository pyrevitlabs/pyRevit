"""Module for managing tags metadata."""
#pylint: disable=E0401,C0111,W0603,C0103,W0703
import re
from collections import namedtuple

from pyrevit.coreutils import logger
from pyrevit import revit, DB

from pkgcommits import CommitPointTypes, CommitTypes
from pkgcommits import CommitPoint, Commit, CommitHistory
import pkgcfg


mlogger = logger.get_logger(__name__)


DocPkg = namedtuple('DocPkg', ['param_name', 'pkg_idx', 'pkg_name'])


class CommitedSheet(object):
    def __init__(self, view_sheet, commit_points):
        commit_cfg = pkgcfg.CommitConfigs()

        self._item = view_sheet
        self._chistory = CommitHistory(commit_points)
        self._read_commit_history(commit_cfg)
        self._ensure_history_start()

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
        commit = self.commit_history.get_commit_at(commit_point)
        return commit or Commit.from_point(commit_point)

    def _read_commit_history(self, commit_cfg):
        # process package commits
        for commit_pt in [x for x in self.commit_history.commit_points
                          if x.cptype == CommitPointTypes.Package]:
            pkg_param = self.revit_sheet.LookupParameter(commit_pt.target)
            if pkg_param:
                ctype = commit_cfg.get_commit_type(pkg_param.AsString())
                # add commit to sheet commits
                if ctype:
                    try:
                        self.commit(commit_pt,
                                    commit_type=ctype)
                    except Exception as e:
                        mlogger.debug(
                            'Commit type "%s" error on %s:%s at %s | (%s) %s',
                            ctype, self.number, self.name, commit_pt,
                            type(e), e
                            )
                    mlogger.debug(self._chistory)

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
                            'Commit type "%s" error on %s:%s at %s | (%s) %s',
                            ctype, self.number, self.name, commit_pt,
                            type(e), e
                            )
                    mlogger.debug(self._chistory)

    def _ensure_history_start(self):
        if not self.commit_history:
            if self.commit_history.commit_points:
                pkg_cpoints = [x for x in self.commit_history.commit_points
                               if x.cptype == CommitPointTypes.Package]
                self.commit(pkg_cpoints[-1], commit_type=CommitTypes.Created)

    def update_commit_history(self):
        commit_cfg = pkgcfg.CommitConfigs()
        # process package commits
        for commit_pt in [x for x in self.commit_history.commit_points
                          if x.cptype == CommitPointTypes.Package]:
            pkg_param = self.revit_sheet.LookupParameter(commit_pt.target)
            if pkg_param:
                commit = self.get_commit_at_point(commit_pt)
                pkg_param.Set(commit_cfg.get_commit_value(commit.commit_type))
            else:
                mlogger.error('Package parameter "%s" does not exist for %s:%s',
                              commit_pt.target, self.number, self.name)

        # process revisions
        all_revs = []
        sheet_revs = []
        for commit_pt in [x for x in self.commit_history.commit_points
                          if x.cptype == CommitPointTypes.Revision]:
            commit = self.get_commit_at_point(commit_pt)
            revision = revit.doc.GetElement(DB.ElementId(commit_pt.target))
            all_revs.append(revision)
            if commit.commit_type == CommitTypes.Revised \
                    and not commit.read_only:
                sheet_revs.append(revision)
        revit.update.update_sheet_revisions(all_revs,
                                            [self.revit_sheet], state=False)
        revit.update.update_sheet_revisions(sheet_revs,
                                            [self.revit_sheet])

    def can_commit(self, commit_point, commit_type,
                   allow_endpoint_change=False):
        return self.commit_history.can_commit_at_point(
            commit_point,
            commit_type,
            allow_endpoint_change=allow_endpoint_change)

    def commit(self, commit_point, commit_type, allow_endpoint_change=False):
        return self.commit_history.commit_at_point(
            commit_point,
            commit_type=commit_type,
            allow_endpoint_change=allow_endpoint_change
            )


def get_commit_points():
    commit_points = []
    # grab defined packages
    dockpkgs = []
    docpkg_finder = \
        re.compile(r'docpkg(\d+)\s*[-_]*?\s*(.+)', flags=re.IGNORECASE)
    for project_param in revit.query.get_project_parameters(doc=revit.doc):
        pkg_match = docpkg_finder.match(project_param.name)
        if pkg_match:
            pkg_idx, pkg_name = pkg_match.groups()
            dockpkgs.append(
                DocPkg(param_name=project_param.name,
                       pkg_idx=int(pkg_idx),
                       pkg_name=pkg_name)
                )

    last_docpkg_idx = 0
    for idx, docpkg in enumerate(sorted(dockpkgs, key=lambda x: x.pkg_idx)):
        last_docpkg_idx = idx
        commit_points.append(
            CommitPoint(cptype=CommitPointTypes.Package,
                        target=docpkg.param_name,
                        idx=idx,
                        name=docpkg.pkg_name))
    # grab revisions
    docrevs = revit.query.get_revisions()
    commit_points.extend([
        CommitPoint(cptype=CommitPointTypes.Revision,
                    target=x.Id.IntegerValue,
                    idx=last_docpkg_idx + i + 1,
                    name=x.Description)
        for i, x in enumerate(docrevs)
        ])

    sorted_cpoints = sorted(commit_points, key=lambda x: x.idx)
    mlogger.debug(sorted_cpoints)
    return sorted_cpoints


def get_commited_sheets():
    commit_points = get_commit_points()

    commited_sheets = []
    doc_sheets = revit.query.get_sheets(include_noappear=False)
    for sheet in doc_sheets:
        cmt_sheet = CommitedSheet(sheet, commit_points)
        commited_sheets.append(cmt_sheet)

    return commited_sheets
