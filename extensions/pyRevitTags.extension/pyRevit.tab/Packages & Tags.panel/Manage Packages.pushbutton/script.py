"""Manage sheet packages."""
#pylint: disable=C0111,E0401,C0103,W0613,W0703
from pyrevit import framework
from pyrevit.framework import wpf
from pyrevit.framework import Windows
from pyrevit import revit
from pyrevit import forms
from pyrevit import script

import pkgmgr
import pkgexceptions
from pkgcommits import CommitPointTypes, CommitTypes, Commit


__title__ = 'Manage\nPackages'

logger = script.get_logger()


NONE_COMMIT_INDEX = -1


class CommitTypeOption:
    def __init__(self, commit_type):
        self.name = commit_type.name
        self.ctype = commit_type
        self.ctypeidx = self.ctype.idx


class CommitItem(object):
    def __init__(self, commit, hasbefore=False, hasafter=False):
        self._commit = commit
        self.hasbefore = hasbefore
        self.hasafter = hasafter

        self.idx = self._commit.idx
        self.ctype = self._commit.ctype
        self.ctypeidx = self.ctype.idx
        self.readonly = self._commit.read_only

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
    def __init__(self, commited_sheet):
        self._commititems = []
        self._csheet = commited_sheet
        self._update_commit_items()

    def _update_commit_items(self):
        commit_items = []
        for commit_pt in self._csheet.commit_history.commit_points:
            commit_items.append(self._get_commit_item(commit_pt))
        # clearn commit items and place passthroughs
        count = False
        self._commititems = []
        for idx, citem in enumerate(commit_items):
            if not citem.has_commit:
                if count and any([x.has_commit for x in commit_items[idx:]]):
                    citem.passthru = True
                self._commititems.append(citem)
            else:
                count = True
                self._commititems.append(citem)

    def _get_commit_item(self, commit_pt):
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
        if pkgmgr.CommitPointTypes.Package.idx in attr_name:
            cidx = int(attr_name.replace(
                pkgmgr.CommitPointTypes.Package.idx, ''))
        elif pkgmgr.CommitPointTypes.Revision.idx in attr_name:
            cidx = int(attr_name.replace(
                pkgmgr.CommitPointTypes.Revision.idx, ''))

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

    def get_commit_at_point(self, commit_point):
        return self._csheet.get_commit_at_point(commit_point)

    def can_commit(self, commit_point, commit_type):
        return self._csheet.can_commit(commit_point, commit_type)

    def commit(self, commit_point, commit_type):
        self._csheet.commit(commit_point,
                            commit_type,
                            allow_endpoint_change=True)
        self._update_commit_items()
        logger.debug(self._csheet.commit_history)

    def update_sheet_history(self):
        self._csheet.update_commit_history()


class ManagePackagesWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        # prepare wpf resources
        self.dt_template = None
        self.package_column_cell_style = \
            self.sheets_dg.Resources['PackageCellStyle']
        self.revision_column_cell_style = \
            self.sheets_dg.Resources['RevisionCellStyle']
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
            commit_column.CellStyle = self.package_column_cell_style
            if commit.cptype == CommitPointTypes.Revision:
                commit_column.CellStyle = self.revision_column_cell_style
            commit_column.CellTemplate = self._make_column_datatemplate(param)
            self.sheets_dg.Columns.Add(commit_column)

    def _list_sheets(self):
        sheets = [SheetItem(x) for x in pkgmgr.get_commited_sheets()]
        # scroll to last column for convenience
        self.sheets_dg.ItemsSource = sorted(sheets, key=lambda x: x.number)
        last_col = list(self.sheets_dg.Columns)[-1]
        self.sheets_dg.ScrollIntoView(sheets[0], last_col)

    def _get_commit_point(self, commit_pt_idx):
        for cp in self._commit_points:
            if cp.idx == commit_pt_idx:
                return cp

    def _ask_for_commit_type(self, sheet_item, commit_pt, commit):
        # allowed_types = []
        # for type_opt in commit.cptype.allowed_commit_types:
        #     if sheet_item.can_commit(commit_pt, type_opt):
        #         allowed_types.append(type_opt)
        ctype_commit_op = forms.SelectFromList.show(
            sorted([CommitTypeOption(x)
                    for x in commit.cptype.allowed_commit_types],
                   key=lambda x: x.ctype.order),
            title='Select Change Type',
            button_name='Apply Change Type',
            width=400,
            height=300,
            item_container_template=self.committype_template
            )
        if ctype_commit_op:
            return ctype_commit_op.ctype

    def edit_commit(self, sender, args):
        if self.sheets_dg.CurrentCell:
            selected_col = self.sheets_dg.CurrentCell.Column
            sheet_item = self.sheets_dg.CurrentCell.Item
            # -2 since sheet name and number are the first two columns
            commit_pt_idx = int(selected_col.DisplayIndex) - 2
            commit_pt = self._get_commit_point(commit_pt_idx)
            commit = sheet_item.get_commit_at_point(commit_pt)
            # cancel if commit is readonly
            if commit.read_only:
                return forms.alert('Change is read-only.')
            commit_type = \
                self._ask_for_commit_type(sheet_item, commit_pt, commit)
            if commit_type:
                try:
                    sheet_item.commit(commit_pt, commit_type)
                except pkgexceptions.HistoryStartMustBeFirst:
                    forms.alert('First change must be a "Create" or '
                                '"Issued for Reference".')
                except pkgexceptions.CanNotUnsetNonExisting:
                    forms.alert('Can not unset a non-existing change.')
                except pkgexceptions.CanNotRemoveStart:
                    forms.alert('Can not unset create in history.')
                except (pkgexceptions.HistoryStartedAfter,
                        pkgexceptions.HistoryStartedBefore):
                    forms.alert('Sheet has already created in history.')
                except (pkgexceptions.HistoryEndedBefore,
                        pkgexceptions.HistoryEndedAfter):
                    forms.alert('Sheet has already deleted/merged in history.')
                except (pkgexceptions.ReadOnlyStart,
                        pkgexceptions.ReadOnlyEnd,
                        pkgexceptions.ReadOnlyCommitInHistory):
                    forms.alert('Read-only change in history.')
            self.sheets_dg.CommitEdit()
            self.sheets_dg.Items.Refresh()

    def update_sheets(self, sender, args):
        self.Close()
        with revit.Transaction('Update Change History'):
            for sheet_item in self.sheets_dg.ItemsSource:
                sheet_item.update_sheet_history()



ManagePackagesWindow('ManagePackagesWindow.xaml').ShowDialog()
