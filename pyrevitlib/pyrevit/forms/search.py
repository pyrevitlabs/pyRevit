"""Modal keyboard search prompts with argument and switch parsing."""

from pyrevit.coreutils.logger import get_logger

mlogger = get_logger(__name__)

from .base import DEFAULT_SEARCHWND_HEIGHT
from .base import DEFAULT_SEARCHWND_WIDTH
from .base import WPFWindow
from .base import XAML_FILES_DIR
from collections import OrderedDict
from pyrevit import PyRevitException
from pyrevit.framework import Input
import os.path as op
from . import _backend


class SearchPrompt(WPFWindow):
    """Standard prompt for pyRevit search.

    Args:
        search_db (list): list of possible search targets
        width (int): width of search prompt window
        height (int): height of search prompt window

    Keyword Args:
        search_tip (str): text to show in grayscale when search box is empty
        switches (str): list of switches

    Returns:
        (tuple[str, dict] | str): matched string if switches are not provided,
            matched strings, and dict of switches otherwise.

    Examples:
        ```python
        from pyrevit import forms
        # assume search input of '/switch1 target1'
        matched_str, args, switches = forms.SearchPrompt.show(
            search_db=['target1', 'target2', 'target3', 'target4'],
            switches=['/switch1', '/switch2'],
            search_tip='pyRevit Search'
            )
        matched_str
        'target1'
        args
        ['--help', '--branch', 'branchname']
        switches
        {'/switch1': True, '/switch2': False}
        ```
    """

    _binding_exclude = True

    def __init__(self, search_db, width, height, **kwargs):
        """Initialize search prompt window."""
        WPFWindow.__init__(self, op.join(XAML_FILES_DIR, "SearchPrompt.xaml"))
        with _backend.disposing(self):
            self.Width = width
            self.MinWidth = self.Width
            self.Height = height

            self.search_tip = kwargs.get("search_tip", "")

            if isinstance(search_db, list):
                self._search_db = {}
                self._search_db_keys = search_db
            elif isinstance(search_db, dict):
                self._search_db = search_db
                self._search_db_keys = sorted(self._search_db.keys())
            else:
                raise PyRevitException("Unknown search database type")

            self._search_res = None
            self._switches = kwargs.get("switches", [])
            self._setup_response()

            self.search_tb.Focus()
            self.hide_element(self.tab_icon)
            self.hide_element(self.return_icon)
            self.search_tb.Text = ""
            self.set_search_results()

    def _setup_response(self, response=None):
        switch_dict = dict.fromkeys(self._switches)
        for switch in self.search_term_switches:
            switch_dict[switch] = True
        arguments = self.search_term_args
        # remove first arg which is command name
        if len(arguments) >= 1:
            arguments = arguments[1:]

        self.response = response, arguments, switch_dict

    @property
    def search_input(self):
        """Current search input."""
        return self.search_tb.Text

    @search_input.setter
    def search_input(self, value):
        self.search_tb.Text = value
        self.search_tb.CaretIndex = len(value)

    @property
    def search_input_parts(self):
        """Current cleaned up search term."""
        return self.search_input.strip().split()

    @property
    def search_term(self):
        """Current cleaned up search term."""
        return self.search_input.lower().strip()

    @property
    def search_term_switches(self):
        """Find matching switches in search term."""
        switches = set()
        for stpart in self.search_input_parts:
            if stpart.lower() in self._switches:
                switches.add(stpart)
        return switches

    @property
    def search_term_args(self):
        """Find arguments in search term."""
        args = []
        switches = self.search_term_switches
        for spart in self.search_input_parts:
            if spart.lower() not in switches:
                args.append(spart)
        return args

    @property
    def search_term_main(self):
        """Current cleaned up search term without the listed switches."""
        if len(self.search_term_args) >= 1:
            return self.search_term_args[0]
        else:
            return ""

    @property
    def search_matches(self):
        """List of matches for the given search term."""
        # remove duplicates while keeping order; list() so callers can index
        # it (dict.keys() is a non-subscriptable view on Python 3)
        return list(OrderedDict.fromkeys(self._search_results))

    def update_results_display(self, fill_match=False):
        """Update search prompt results based on current input text."""
        self.directmatch_tb.Text = ""
        self.wordsmatch_tb.Text = ""

        results = self.search_matches
        res_cout = len(results)

        mlogger.debug("unique results count: %s", res_cout)
        mlogger.debug("unique results: %s", results)

        if res_cout > 1:
            self.show_element(self.tab_icon)
            self.hide_element(self.return_icon)
        elif res_cout == 1:
            self.hide_element(self.tab_icon)
            self.show_element(self.return_icon)
        else:
            self.hide_element(self.tab_icon)
            self.hide_element(self.return_icon)

        if self._result_index >= res_cout:
            self._result_index = 0  # pylint: disable=W0201

        if self._result_index < 0:
            self._result_index = res_cout - 1  # pylint: disable=W0201

        if not self.search_input:
            self.directmatch_tb.Text = self.search_tip
            return

        if results:
            input_term = self.search_term
            cur_res = results[self._result_index]
            mlogger.debug("current result: %s", cur_res)
            if fill_match:
                self.search_input = cur_res
            else:
                if cur_res.lower().startswith(input_term):
                    self.directmatch_tb.Text = (
                        self.search_input + cur_res[len(input_term) :]
                    )
                    mlogger.debug("directmatch_tb.Text: %s", self.directmatch_tb.Text)
                else:
                    self.wordsmatch_tb.Text = "- {}".format(cur_res)
                    mlogger.debug("wordsmatch_tb.Text: %s", self.wordsmatch_tb.Text)
            tooltip = self._search_db.get(cur_res, None)
            if tooltip:
                self.tooltip_tb.Text = tooltip
                self.show_element(self.tooltip_tb)
            else:
                self.hide_element(self.tooltip_tb)
            self._search_res = cur_res
            return True
        return False

    def set_search_results(self, *args):
        """Set search results for returning."""
        self._result_index = 0
        self._search_results = []

        mlogger.debug("search input: %s", self.search_input)
        mlogger.debug("search term: %s", self.search_term)
        mlogger.debug("search term (main): %s", self.search_term_main)
        mlogger.debug("search term (parts): %s", self.search_input_parts)
        mlogger.debug("search term (args): %s", self.search_term_args)
        mlogger.debug("search term (switches): %s", self.search_term_switches)

        for resultset in args:
            mlogger.debug("result set: %s}", resultset)
            self._search_results.extend(sorted(resultset))

        mlogger.debug("results: %s", self._search_results)

    def find_direct_match(self, input_text):
        """Find direct text matches in search term."""
        results = []
        if input_text:
            for cmd_name in self._search_db_keys:
                if cmd_name.lower().startswith(input_text):
                    results.append(cmd_name)

        return results

    def find_word_match(self, input_text):
        """Find direct word matches in search term."""
        results = []
        if input_text:
            cur_words = input_text.split(" ")
            for cmd_name in self._search_db_keys:
                if all([x in cmd_name.lower() for x in cur_words]):
                    results.append(cmd_name)

        return results

    def search_txt_changed(self, sender, args):  # pylint: disable=W0613
        """Handle text changed event."""
        input_term = self.search_term_main
        dmresults = self.find_direct_match(input_term)
        wordresults = self.find_word_match(input_term)
        self.set_search_results(dmresults, wordresults)
        self.update_results_display()

    def handle_kb_key(self, sender, args):  # pylint: disable=W0613
        """Handle keyboard input event."""
        shiftdown = Input.Keyboard.IsKeyDown(
            Input.Key.LeftShift
        ) or Input.Keyboard.IsKeyDown(Input.Key.RightShift)
        # Escape: set response to none and close
        if args.Key == Input.Key.Escape:
            self._setup_response()
            self.Close()
        # Enter: close, returns matched response automatically
        elif args.Key == Input.Key.Enter:
            if self.search_tb.Text != "":
                self._setup_response(response=self._search_res)
                args.Handled = True
                self.Close()
        # Shift+Tab, Tab: Cycle through matches
        elif args.Key == Input.Key.Tab and shiftdown:
            self._result_index -= 1
            self.update_results_display()
        elif args.Key == Input.Key.Tab:
            self._result_index += 1
            self.update_results_display()
        # Up, Down: Cycle through matches
        elif args.Key == Input.Key.Up:
            self._result_index -= 1
            self.update_results_display()
        elif args.Key == Input.Key.Down:
            self._result_index += 1
            self.update_results_display()
        # Right, End: Autocomplete with displayed match
        elif args.Key in [Input.Key.Right, Input.Key.End]:
            self.update_results_display(fill_match=True)

    @classmethod
    def show(
        cls,
        search_db,  # pylint: disable=W0221
        width=DEFAULT_SEARCHWND_WIDTH,
        height=DEFAULT_SEARCHWND_HEIGHT,
        **kwargs
    ):  # fmt: skip
        """Show search prompt."""
        dlg = cls(search_db, width, height, **kwargs)
        dlg.ShowDialog()
        return dlg.response
