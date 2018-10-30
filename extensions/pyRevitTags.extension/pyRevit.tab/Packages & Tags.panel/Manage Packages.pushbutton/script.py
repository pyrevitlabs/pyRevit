"""Manage sheet packages."""
#pylint: disable=C0111,E0401,C0103,W0613,W0703
from pyrevit import framework
from pyrevit.framework import wpf
from pyrevit.framework import Windows
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

import pkgmgr
from pkgcommits import CommitTypes, Commit


__title__ = 'Manage\nPackages'

logger = script.get_logger()


NONE_COMMIT_INDEX = -1


class CommitTypeOption:
    def __init__(self, name, ctype=CommitTypes.NotSet):
        self.name = name
        self.ctype = ctype


class CommitItem(object):
    def __init__(self, commit, hasbefore=False, hasafter=False):
        self._commit = commit
        self.hasbefore = hasbefore
        self.hasafter = hasafter

        self.idx = self._commit.idx
        self.ctype = self._commit.ctype

    @property
    def has_commit(self):
        return self.ctype != CommitTypes.NotSet

    @property
    def passthru(self):
        return self.hasbefore and self.hasafter \
            and self.ctype == CommitTypes.NotSet

    @passthru.setter
    def passthru(self, value):
        self.hasbefore = self.hasafter = True
        self.ctype = CommitTypes.NotSet

    @property
    def linebefore(self):
        if self.hasbefore:
            return forms.WPF_VISIBLE

    @property
    def linethru(self):
        if self.passthru:
            return forms.WPF_VISIBLE

    @property
    def lineafter(self):
        if self.hasafter:
            return forms.WPF_VISIBLE


class SheetItem(object):
    def __init__(self, commited_sheet, commit_points):
        self._commititems = []
        self._csheet = commited_sheet
        self._update_commit_items(commit_points)

    def _update_commit_items(self, commit_points):
        commititems = []
        for commit_pt in commit_points:
            commititems.append(self._get_commititem(commit_pt))
        # clearn commit items and place passthroughs
        count = False
        self._commititems = []
        for idx, citem in enumerate(commititems):
            if not citem.has_commit:
                if count and any([x.has_commit for x in commititems[idx:]]):
                    citem.passthru = True
                self._commititems.append(citem)
            else:
                count = True
                self._commititems.append(citem)

    def _get_commititem(self, commit_pt):
        for commit in self._csheet.commit_history:
            if commit.is_at(commit_pt):
                prev_commit = self._csheet.commit_history.get_prev(commit)
                next_commit = self._csheet.commit_history.get_next(commit)
                return CommitItem(commit,
                                  hasbefore=prev_commit is not None,
                                  hasafter=next_commit is not None)
        return CommitItem(Commit.from_point(commit_pt))

    def __getattr__(self, attr_name):
        # is this a sorting attribute? if yes, return index numbers
        sort_mode = False
        if 'sort_' in attr_name:
            attr_name = attr_name.replace('sort_', '')
            sort_mode = True

        cidx = None
        if pkgmgr.CommitTargets.Package in attr_name:
            cidx = int(attr_name.replace(pkgmgr.CommitTargets.Package, ''))
        elif pkgmgr.CommitTargets.Revision in attr_name:
            cidx = int(attr_name.replace(pkgmgr.CommitTargets.Revision, ''))

        citem = None
        if cidx is not None:
            citem = self._commititems[cidx]

        if sort_mode:
            if citem.has_commit:
                return citem.idx
            else:
                return NONE_COMMIT_INDEX

        return citem

    @property
    def name(self):
        return self._csheet.name

    @property
    def number(self):
        return self._csheet.number

    @staticmethod
    def build_commit_param(commit):
        return '{}{}'.format(commit.cptype, commit.idx)

    @staticmethod
    def build_commit_sort_param(commit):
        return 'sort_{}{}'.format(commit.cptype, commit.idx)

    def commit(self, commit_point, commit_type, commit_points):
        self._csheet.commit(commit_point, commit_type)
        self._update_commit_items(commit_points)


class ManagePackagesWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        # prepare wpf resources
        self.dt_template = None
        self.commit_column_cell_style = \
            self.sheets_dg.Resources['DefaultTemplateCellStyle']
        self.committype_template = \
            self.Resources["CommitTypeListItemControlTemplate"]
        self._read_resources()

        # grab doc commits
        self._commit_points = pkgmgr.get_commit_points()
        # prepare columns
        self._build_columns()

        # list all sheets
        self._list_sheets()

        self.last_selected_number = ''

    def _read_resources(self):
        dt_template_file = script.get_bundle_file('PackagesDataTemplate.xaml')
        with open(dt_template_file, 'r') as dt_file:
            self.dt_template = dt_file.read()

    def _make_column_datatemplate(self, package_param_name):
        dtobj = Windows.DataTemplate()
        template = self.dt_template.format(param=package_param_name)
        return wpf.LoadComponent(dtobj, framework.StringReader(template))

    def _build_columns(self):
        for commit in self._commit_points:
            param = SheetItem.build_commit_param(commit)
            sort_param = SheetItem.build_commit_sort_param(commit)
            commit_column = Windows.Controls.DataGridTemplateColumn()
            commit_column.Header = commit.name
            commit_column.CanUserSort = True
            commit_column.SortMemberPath = sort_param
            # commit_column.SortDirection = \
            #     ComponentModel.ListSortDirection.Descending
            commit_column.CellStyle = self.commit_column_cell_style
            commit_column.CellTemplate = self._make_column_datatemplate(param)
            self.sheets_dg.Columns.Add(commit_column)

    def _list_sheets(self):
        sheets = [SheetItem(x, self._commit_points)
                  for x in pkgmgr.get_commited_sheets()]
        # scroll to last column for convenience
        self.sheets_dg.ItemsSource = sorted(sheets, key=lambda x: x.number)
        last_col = list(self.sheets_dg.Columns)[-1]
        self.sheets_dg.ScrollIntoView(sheets[0], last_col)

    def _get_commit_point(self, commit_pt_idx):
        for cp in self._commit_points:
            if cp.idx == commit_pt_idx:
                return cp

    def _ask_fro_commit_type(self):
        options = [CommitTypeOption(name='Not Set', ctype=CommitTypes.NotSet)]
        options.extend(
            [CommitTypeOption(x, ctype=getattr(CommitTypes, x))
             for x in dir(CommitTypes)
             if not x.startswith('__') and x != 'NotSet'])
        ctype_commit = forms.SelectFromList.show(
            options,
            title='Select Change Type',
            button_name='Apply Change Type',
            width=400,
            height=300,
            item_container_template=self.committype_template
            )
        if ctype_commit:
            return ctype_commit.ctype

    def mouse_up(self, sender, args):
        if self.sheets_dg.CurrentCell:
            selected_col = self.sheets_dg.CurrentCell.Column
            # -2 since sheet name and number are the first two columns
            commit_pt_idx = int(selected_col.DisplayIndex) - 2
            commit_pt = self._get_commit_point(commit_pt_idx)
            commit_type = self._ask_fro_commit_type()
            if commit_type:
                self.sheets_dg.CurrentCell.Item.commit(
                    commit_pt, commit_type, self._commit_points
                    )
            self.sheets_dg.CommitEdit()
            self.sheets_dg.Items.Refresh()

    def update_sheets(self, sender, args):
        self.Close()
        # update sheets



ManagePackagesWindow('ManagePackagesWindow.xaml').ShowDialog()
