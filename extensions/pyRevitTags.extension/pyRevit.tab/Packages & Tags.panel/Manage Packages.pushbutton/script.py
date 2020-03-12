"""Manage sheet packages."""
#pylint: disable=C0111,E0401,C0103,W0613,W0703
from pyrevit import framework
from pyrevit.framework import wpf
from pyrevit.framework import Windows
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

import pkgmgr
import pkgexceptions
from pkgcommits import CommitPointTypes, CommitTypes, Commit


__title__ = 'Manage\nPackages'
__author__ = '{{author}}'
__helpurl__ = '{{docpath}}po0lCldSGmk'

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

        self.idx = self._commit.commit_point.idx
        self.ctype = self._commit.commit_type
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
                prev_commit = \
                    self._csheet.commit_history.get_prev_commit(commit)
                next_commit = \
                    self._csheet.commit_history.get_next_commit(commit)
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

    def __repr__(self):
        return '<{} no:{}>'.format(self.__class__.__name__, self.number)

    @property
    def name(self):
        return self._csheet.name

    @property
    def number(self):
        return self._csheet.number

    @staticmethod
    def build_commit_param(commit_point):
        return '{}{}'.format(commit_point.cptype, commit_point.idx)

    @staticmethod
    def build_commit_sort_param(commit_point):
        return 'sort_{}{}'.format(commit_point.cptype, commit_point.idx)

    def get_order(self, param_name):
        return self._csheet.revit_sheet.LookupParameter(param_name).AsInteger()

    def get_commit_at_point(self, commit_point):
        return self._csheet.get_commit_at_point(commit_point)

    def can_commit(self, commit_point, commit_type):
        return self._csheet.can_commit(commit_point,
                                       commit_type,
                                       allow_endpoint_change=True)

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
        selection = revit.get_selection()
        sel_cnt = len(selection)
        if sel_cnt:
            forms.alert('You are managing packages on {} selected sheets only.'
                        .format(sel_cnt))

        forms.WPFWindow.__init__(self, xaml_file_name)

        # prepare default privates
        self._last_filter_len = 0

        # prepare wpf resources
        self.dt_template = None
        self.package_column_cell_style = \
            self.sheets_dg.Resources['PackageCellStyle']
        self.revision_column_cell_style = \
            self.sheets_dg.Resources['RevisionCellStyle']
        self.committype_template = \
            self.Resources["CommitTypeListItemControlTemplate"]
        self._read_resources()

        # grab commit points
        self._commit_points = pkgmgr.get_commit_points()
        # prepare columns
        self._build_columns()

        # collect sheets and wrap in sheetitem
        committed_sheets = pkgmgr.get_commited_sheets()
        sheet_numbers = [x.SheetNumber
                         for x in selection if isinstance(x, DB.ViewSheet)]

        if sheet_numbers:
            sheetitems = [SheetItem(x) for x in committed_sheets
                          if x.number in sheet_numbers]
        else:
            sheetitems = [SheetItem(x) for x in committed_sheets]

        self._sheetitems = sorted(sheetitems, key=lambda x: x.number)
        self._setup_item_params_combobox(committed_sheets)

        # list all sheets
        self._list_sheets()
        if isinstance(revit.active_view, DB.ViewSheet):
            self.search_tb.Text = revit.active_view.SheetNumber

    def _read_resources(self):
        dt_template_file = script.get_bundle_file('PackagesDataTemplate.xaml')
        with open(dt_template_file, 'r') as dt_file:
            self.dt_template = dt_file.read()

    def _make_column_datatemplate(self, package_param_name):
        dtobj = Windows.DataTemplate()
        template = self.dt_template.format(param=package_param_name)
        return wpf.LoadComponent(dtobj, framework.StringReader(template))

    def _build_columns(self):
        for commit_point in self._commit_points:
            param = SheetItem.build_commit_param(commit_point)
            sort_param = SheetItem.build_commit_sort_param(commit_point)
            commit_column = Windows.Controls.DataGridTemplateColumn()
            commit_column.Header = commit_point.name
            commit_column.CanUserSort = True
            commit_column.MinWidth = 50
            commit_column.SortMemberPath = sort_param
            # commit_column.SortDirection = \
            #     ComponentModel.ListSortDirection.Descending
            commit_column.CellStyle = self.package_column_cell_style
            if commit_point.cptype == CommitPointTypes.Revision:
                commit_column.CellStyle = self.revision_column_cell_style
            commit_column.CellTemplate = self._make_column_datatemplate(param)
            self.sheets_dg.Columns.Add(commit_column)

    def _list_sheets(self, sheet_filter=None):
        if not self.sheets_dg.ItemsSource or not sheet_filter:
            items_source = list(self._sheetitems)
        else:
            items_source = self.sheets_dg.ItemsSource

        if sheet_filter:
            sheet_filter = sheet_filter.lower()
            sheet_filter_len = len(sheet_filter)
            # if backspacing, reset the sheet list
            if self._last_filter_len > sheet_filter_len:
                items_source = list(self._sheetitems)

            items_source = \
                [x for x in items_source
                 if sheet_filter in x.number.lower()
                 or sheet_filter in x.name.lower()]

            self._last_filter_len = sheet_filter_len

        if self.sheetorder_param:
            param = self.sheetorder_param
            items_source = \
                sorted(items_source, key=lambda x: x.get_order(param))

        self.sheets_dg.ItemsSource = items_source
        # update misc gui items
        if len(self.sheets_dg.ItemsSource) > 1:
            self.updatesheets_b.Content = "Update Sheets"
        else:
            self.updatesheets_b.Content = "Update Sheet"
        # scroll to last column for convenience
        if self.sheets_dg.ItemsSource:
            self.sheets_dg.ScrollIntoView(
                self.sheets_dg.ItemsSource[0],
                list(self.sheets_dg.Columns)[-1]
                )

    def _get_commit_point(self, commit_pt_idx):
        for commit_point in self._commit_points:
            if commit_point.idx == commit_pt_idx:
                return commit_point

    def _ask_for_commit_type(self, sheet_item, commit_pt, commit):
        allowed_types = []
        for type_opt in commit.commit_point.cptype.allowed_commit_types:
            if sheet_item.can_commit(commit_pt, type_opt):
                allowed_types.append(type_opt)
        # allowed_types = commit.commit_point.cptype.allowed_commit_types
        if allowed_types:
            ctype_commit_op = forms.SelectFromList.show(
                sorted([CommitTypeOption(x)
                        for x in allowed_types],
                       key=lambda x: x.ctype.order),
                title='Select Change Type',
                button_name='Apply Change Type',
                width=400,
                height=300,
                item_template=self.committype_template
                )
            if ctype_commit_op:
                return ctype_commit_op.ctype
        else:
            forms.alert('No changes is allowed at this point.')

    def _setup_item_params_combobox(self, committed_sheets):
        if committed_sheets:
            csheet = committed_sheets[0]
            sheet_params = \
                [x.Definition.Name for x in csheet.revit_sheet.Parameters
                 if x.StorageType == DB.StorageType.Integer]
            order_params = [x for x in sheet_params if 'order' in x.lower()]
            if order_params:
                self.orderparams_cb.ItemsSource = sorted(order_params)
                self.orderparams_cb.SelectedIndex = 0
                self.sheetordering_options.IsEnabled = True
                self.show_element(self.sheetordering_options)

    @property
    def sheetorder_param(self):
        if self.sheetordering_options.IsEnabled:
            return self.orderparams_cb.SelectedItem

    def update_list(self, sender, args):
        """Handle text change in search box."""
        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        self._list_sheets(sheet_filter=self.search_tb.Text)

    def clear_search(self, sender, args):
        """Clear search box."""
        self.search_tb.Text = ' '
        self.search_tb.Clear()
        self.search_tb.Focus()

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
                except pkgexceptions.ReadOnlyCommitInHistory:
                    forms.alert('Read-only change in history.')
            self.sheets_dg.CommitEdit()
            self.sheets_dg.Focus()
            self.sheets_dg.Items.Refresh()
        args.Cancel = True

    def update_sheets(self, sender, args):
        self.Close()
        with revit.Transaction('Update Change History'):
            for sheet_item in self.sheets_dg.ItemsSource:
                sheet_item.update_sheet_history()


# make sure doc is not family
forms.check_modeldoc(doc=revit.doc, exitscript=True)

ManagePackagesWindow('ManagePackagesWindow.xaml').ShowDialog()
