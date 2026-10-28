"""Grouped and searchable selection dialogs shared by both Python engines."""

from .base import DEFAULT_INPUTWINDOW_HEIGHT
from .base import DEFAULT_INPUTWINDOW_WIDTH
from .dialogs import TemplateUserInputWindow
from .reactive import TemplateListItem
from collections import OrderedDict
from pyrevit import PyRevitException
from pyrevit import coreutils
from pyrevit.framework import Controls
from pyrevit.framework import System
import re
import sys
from . import _backend
from pyrevit.coreutils.logger import get_logger

mlogger = get_logger(__name__)


class SelectFromList(TemplateUserInputWindow):
    """Standard form to select from a list of items.

    Any object can be passed in a list to the ``context`` argument. This class
    wraps the objects passed to context, in `TemplateListItem`.
    This class provides the necessary mechanism to make this form work both
    for selecting items from a list, and from a list of checkboxes. See the
    list of arguments below for additional options and features.

    Args:
        context (list[str] or dict[list[str]]):
            list of items to be selected from
            OR
            dict of list of items to be selected from.
            use dict when input items need to be grouped
            e.g. List of sheets grouped by sheet set.
        title (str, optional): window title. see super class for defaults.
        width (int, optional): window width. see super class for defaults.
        height (int, optional): window height. see super class for defaults.

    Keyword Args:
        button_name (str, optional):
            name of select button. defaults to 'Select'
        name_attr (str, optional):
            object attribute that should be read as item name.
        multiselect (bool, optional):
            allow multi-selection (uses check boxes). defaults to False
        info_panel (bool, optional):
            show information panel and fill with .description property of item
        return_all (bool, optional):
            return all items. This is handly when some input items have states
            and the script needs to check the state changes on all items.
            This options works in multiselect mode only. defaults to False
        filterfunc (function):
            filter function to be applied to context items.
        resetfunc (function):
            reset function to be called when user clicks on Reset button
        group_selector_title (str):
            title for list group selector. defaults to 'List Group'
        default_group (str): name of defautl group to be selected
        sort_groups (str, optional):
            Determines the sorting type applied to the list groups. This attribute can take one of the following values:
                'sorted': This will sort the groups in standard alphabetical order
                'natural': This will sort the groups in a manner that is more intuitive for human perception, especially when there are numbers involved.
                'unsorted': The groups will maintain the original order in which they were provided, without any reordering.
                Defaults to 'sorted'.

    Examples:
        ```python
        from pyrevit import forms
        items = ['item1', 'item2', 'item3']
        forms.SelectFromList.show(items, button_name='Select Item')
        ['item1']
        ```
        ```python
        from pyrevit import forms
        ops = [viewsheet1, viewsheet2, viewsheet3]
        res = forms.SelectFromList.show(ops,
                                        multiselect=False,
                                        name_attr='Name',
                                        button_name='Select Sheet')
        ```

        ```python
        from pyrevit import forms
        ops = {'Sheet Set A': [viewsheet1, viewsheet2, viewsheet3],
               'Sheet Set B': [viewsheet4, viewsheet5, viewsheet6]}
        res = forms.SelectFromList.show(ops,
                                        multiselect=True,
                                        name_attr='Name',
                                        group_selector_title='Sheet Sets',
                                        button_name='Select Sheets',
                                        sort_groups='sorted')
        ```

        This module also provides a wrapper base class :obj:`TemplateListItem`
        for when the checkbox option is wrapping another element,
        e.g. a Revit ViewSheet. Derive from this base class and define the
        name property to customize how the checkbox is named on the dialog.

        ```python
        from pyrevit import forms
        class MyOption(forms.TemplateListItem):
           @property
           def name(self):
               return '{} - {}{}'.format(self.item.SheetNumber,
                                         self.item.SheetNumber)
        ops = [MyOption('op1'), MyOption('op2', True), MyOption('op3')]
        res = forms.SelectFromList.show(ops,
                                        multiselect=True,
                                        button_name='Select Item')
        [bool(x) for x in res]  # or [x.state for x in res]
        [True, False, True]
        ```

    """

    in_check = False
    in_uncheck = False
    xaml_source = "SelectFromList.xaml"
    default_title_key = "SelectFromList.DefaultTitle"
    resolve_theme = True

    @property
    def use_regex(self):
        """Is using regex?"""
        return self.regexToggle_b.IsChecked

    def _setup(self, **kwargs):
        # custom button name?
        button_name = kwargs.get("button_name", None)
        if button_name is not None:
            # Only override Content when caller provides a custom button name.
            # When button_name is None, let the XAML DynamicResource binding
            # defined in SelectFromList.xaml control the button content.
            self.select_b.Content = button_name
        else:
            self.select_b.Content = self.get_locale_string(
                "SelectFromList.Select.Button", "Select"
            )

        # attribute to use as name?
        self._nameattr = kwargs.get("name_attr", None)

        # multiselect?
        if kwargs.get("multiselect", False):
            self.multiselect = True
            self.list_lb.SelectionMode = Controls.SelectionMode.Extended
            self.show_element(self.checkboxbuttons_g)
        else:
            self.multiselect = False
            self.list_lb.SelectionMode = Controls.SelectionMode.Single
            self.hide_element(self.checkboxbuttons_g)

        # info panel?
        self.info_panel = kwargs.get("info_panel", False)

        # return checked items only?
        self.return_all = kwargs.get("return_all", False)

        # filter function?
        self.filter_func = kwargs.get("filterfunc", None)

        # reset function?
        self.reset_func = kwargs.get("resetfunc", None)
        if self.reset_func:
            self.show_element(self.reset_b)

        # context group title?
        self.ctx_groups_title = kwargs.get("group_selector_title")
        if self.ctx_groups_title:
            self.ctx_groups_title_tb.Text = self.ctx_groups_title
        else:
            # Let XAML DynamicResource provide the actual Text value.
            # The python-side self.ctx_groups_title is used for internal logic
            # and needs a safe fallback.
            self.ctx_groups_title = self.get_locale_string(
                "SelectFromList.GroupSelector.Label", "Groups"
            )

        self.ctx_groups_active = kwargs.get("default_group", None)

        # group sorting?
        self.sort_groups = kwargs.get("sort_groups", "sorted")
        if self.sort_groups not in ["sorted", "unsorted", "natural"]:
            raise PyRevitException(
                "Invalid value for 'sort_groups'. Allowed values are: 'sorted', 'unsorted', 'natural'."
            )

        # check for custom templates
        items_panel_template = kwargs.get("items_panel_template", None)
        if items_panel_template:
            self.Resources["ItemsPanelTemplate"] = items_panel_template

        item_container_template = kwargs.get("item_container_template", None)
        if item_container_template:
            self.Resources["ItemContainerTemplate"] = item_container_template

        item_template = kwargs.get("item_template", None)
        if item_template:
            self.Resources["ItemTemplate"] = item_template

        # nicely wrap and prepare context for presentation, then present
        self._prepare_context()

        # setup search and filter fields
        self.hide_element(self.clrsearch_b)

        # active event listeners
        _backend.bind_control_event(
            self, self.search_tb, "TextChanged", self.search_txt_changed
        )
        _backend.bind_control_event(
            self,
            self.ctx_groups_selector_cb,
            "SelectionChanged",
            self.selection_changed,
        )

        self.clear_search(None, None)

    def _prepare_context_items(self, ctx_items):
        new_ctx = []
        # filter context if necessary
        if self.filter_func:
            ctx_items = filter(self.filter_func, ctx_items)

        for item in ctx_items:
            if isinstance(item, TemplateListItem):
                item.checkable = self.multiselect
                new_ctx.append(item)
            else:
                new_ctx.append(
                    TemplateListItem(
                        item, checkable=self.multiselect, name_attr=self._nameattr
                    )
                )

        return new_ctx

    @staticmethod
    def _natural_sort_key(key):
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", key)]

    def _prepare_context(self):
        if isinstance(self._context, dict) and self._context.keys():
            # Sort the groups if necessary
            if self.sort_groups == "sorted":
                sorted_groups = sorted(self._context.keys())
            elif self.sort_groups == "natural":
                sorted_groups = sorted(self._context.keys(), key=self._natural_sort_key)
            else:
                # list() so downstream .index()/binding works (dict.keys()
                # is a non-indexable view on Python 3)
                sorted_groups = list(self._context.keys())  # No sorting

            self._update_ctx_groups(sorted_groups)

            new_ctx = OrderedDict()
            for ctx_grp in sorted_groups:
                items = self._prepare_context_items(self._context[ctx_grp])
                new_ctx[ctx_grp] = items  # Do not sort the items within the groups

            self._context = new_ctx
        else:
            self._context = self._prepare_context_items(self._context)

    def _update_ctx_groups(self, ctx_group_names):
        self.show_element(self.ctx_groups_dock)
        self.ctx_groups_selector_cb.ItemsSource = _backend.items_source(ctx_group_names)
        if self.ctx_groups_active in ctx_group_names:
            self.ctx_groups_selector_cb.SelectedIndex = ctx_group_names.index(
                self.ctx_groups_active
            )
        else:
            self.ctx_groups_selector_cb.SelectedIndex = 0

    def _get_active_ctx_group(self):
        return self.ctx_groups_selector_cb.SelectedItem

    def _get_active_ctx(self):
        if isinstance(self._context, dict):
            return self._context[self._get_active_ctx_group()]
        else:
            return self._context

    def _get_all_ctx(self):
        """Get all context items across all groups."""
        ctx = self._context
        if ctx is None:
            return

        if isinstance(ctx, dict):
            seen_ids = set()
            for group_items in ctx.values():
                for item in group_items:
                    if id(item) not in seen_ids:
                        seen_ids.add(id(item))
                        yield item
        elif isinstance(ctx, (list, tuple, set)):
            for item in ctx:
                yield item
        else:
            yield ctx

    def _list_options(self, option_filter=None):
        if option_filter:
            self.checkall_b.Content = self.get_locale_string(
                "SelectFromList.Check.Button", "Check"
            )
            self.uncheckall_b.Content = self.get_locale_string(
                "SelectFromList.Uncheck.Button", "Uncheck"
            )
            self.toggleall_b.Content = self.get_locale_string(
                "SelectFromList.Toggle.Button", "Toggle"
            )
            # get a match score for every item and sort high to low
            fuzzy_matches = sorted(
                [
                    (
                        x,
                        coreutils.fuzzy_search_ratio(
                            target_string=x.name,
                            sfilter=option_filter,
                            regex=self.use_regex,
                        ),
                    )
                    for x in self._get_active_ctx()
                ],
                key=lambda x: x[1],
                reverse=True,
            )
            # filter out any match with score less than 80
            self.list_lb.ItemsSource = _backend.list_source(
                [x[0] for x in fuzzy_matches if x[1] >= 80]
            )
        else:
            self.checkall_b.Content = self.get_locale_string(
                "SelectFromList.CheckAll.Button", "Check All"
            )
            self.uncheckall_b.Content = self.get_locale_string(
                "SelectFromList.UncheckAll.Button", "Uncheck All"
            )
            self.toggleall_b.Content = self.get_locale_string(
                "SelectFromList.ToggleAll.Button", "Toggle All"
            )

            self.list_lb.ItemsSource = _backend.list_source(self._get_active_ctx())

    @staticmethod
    def _unwrap_options(options):
        unwrapped = []
        for optn in options:
            optn = _backend.unwrap_item(optn)
            if isinstance(optn, TemplateListItem):
                unwrapped.append(optn.unwrap())
            else:
                unwrapped.append(optn)
        return unwrapped

    def _get_options(self):
        if self.multiselect:
            if self.return_all:
                return list(self._get_all_ctx())
            else:
                selected = {
                    id(_backend.unwrap_item(item))
                    for item in self.list_lb.SelectedItems
                }
                return self._unwrap_options(
                    [x for x in self._get_all_ctx() if x.state or id(x) in selected]
                )
        else:
            return self._unwrap_options([self.list_lb.SelectedItem])[0]

    def _set_states(self, state=True, flip=False, selected=False):
        if selected:
            current_list = self.list_lb.SelectedItems
        else:
            current_list = self.list_lb.ItemsSource
        for checkbox in current_list:
            checkbox = _backend.unwrap_item(checkbox)
            # using .checked to push ui update
            if flip:
                checkbox.checked = not checkbox.checked
            else:
                checkbox.checked = state

    def _toggle_info_panel(self, state=True):
        if state:
            # enable the info panel
            self.splitterCol.Width = System.Windows.GridLength(8)
            self.infoCol.Width = System.Windows.GridLength(self.Width / 2)
            self.show_element(self.infoSplitter)
            self.show_element(self.infoPanel)
        else:
            self.splitterCol.Width = self.infoCol.Width = System.Windows.GridLength.Auto
            self.hide_element(self.infoSplitter)
            self.hide_element(self.infoPanel)

    def toggle_all(self, sender, args):  # pylint: disable=W0613
        """Handle toggle all button to toggle state of all check boxes."""
        self._set_states(flip=True)

    def check_all(self, sender, args):  # pylint: disable=W0613
        """Handle check all button to mark all check boxes as checked."""
        self._set_states(state=True)

    def uncheck_all(self, sender, args):  # pylint: disable=W0613
        """Handle uncheck all button to mark all check boxes as un-checked."""
        self._set_states(state=False)

    def check_selected(self, sender, args):  # pylint: disable=W0613
        """Mark selected checkboxes as checked."""
        if not self.in_check:
            try:
                self.in_check = True
                item = _backend.unwrap_item(sender.DataContext)
                if isinstance(item, TemplateListItem):
                    item.checked = True
                self._set_states(state=True, selected=True)
            finally:
                self.in_check = False

    def uncheck_selected(self, sender, args):  # pylint: disable=W0613
        """Mark selected checkboxes as unchecked."""
        if not self.in_uncheck:
            try:
                self.in_uncheck = True
                item = _backend.unwrap_item(sender.DataContext)
                if isinstance(item, TemplateListItem):
                    item.checked = False
                self._set_states(state=False, selected=True)
            finally:
                self.in_uncheck = False

    def button_reset(self, sender, args):  # pylint: disable=W0613
        """Pass the listed items to ``resetfunc`` and keep its changes visible.

        Note:
            IronPython passes the live ``ItemsSource`` collection. CPython binds
            managed proxies, so it passes the original Python items instead and
            rebinds the list when ``resetfunc`` adds, removes or reorders them.
        """
        if not self.reset_func:
            return
        items_source = self.list_lb.ItemsSource
        all_items = [_backend.unwrap_item(item) for item in items_source]
        if all(item is native for item, native in zip(all_items, items_source)):
            self.reset_func(items_source)
            return
        listed_items = list(all_items)
        self.reset_func(all_items)
        if len(all_items) != len(listed_items) or any(
            item is not listed for item, listed in zip(all_items, listed_items)
        ):
            self.list_lb.ItemsSource = _backend.list_source(all_items)

    def button_select(self, sender, args):  # pylint: disable=W0613
        """Handle select button click."""
        self.response = self._get_options()
        self.Close()

    def search_txt_changed(self, sender, args):  # pylint: disable=W0613
        """Handle text change in search box."""
        if self.info_panel:
            self._toggle_info_panel(state=False)

        if self.search_tb.Text == "":
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        self._list_options(option_filter=self.search_tb.Text)

    def selection_changed(self, sender, args):
        """Handle selection change."""
        if self.info_panel:
            self._toggle_info_panel(state=False)

        self._list_options(option_filter=self.search_tb.Text)

    def selected_item_changed(self, sender, args):
        """Handle selected item change."""
        if self.info_panel and self.list_lb.SelectedItem is not None:
            self._toggle_info_panel(state=True)
            self.infoData.Text = getattr(
                _backend.unwrap_item(self.list_lb.SelectedItem), "description", ""
            )

    def toggle_regex(self, sender, args):
        """Activate regex in search."""
        self.regexToggle_b.Content = (
            self.Resources["regexIcon"]
            if self.use_regex
            else self.Resources["filterIcon"]
        )
        self.search_txt_changed(sender, args)
        self.search_tb.Focus()

    def clear_search(self, sender, args):  # pylint: disable=W0613
        """Clear search box."""
        self.search_tb.Text = " "
        self.search_tb.Clear()
        self.search_tb.Focus()

    @classmethod
    def show(
        cls,
        context,
        title=None,
        width=DEFAULT_INPUTWINDOW_WIDTH,
        height=DEFAULT_INPUTWINDOW_HEIGHT,
        exitscript=False,
        **kwargs
    ):  # fmt: skip
        """Show user input window.

        Args:
            context (any): window context element(s)
            title (str): window title.
            width: ...
            height: ...
            exitscript: exit the script if the user cancels the dialog. Defaults to False
            **kwargs: Dialog configuration passed to the window.
        """
        dlg = cls(context, title, width, height, **kwargs)
        dlg.ShowDialog()
        if exitscript and not dlg.response:
            sys.exit()
        return dlg.response
