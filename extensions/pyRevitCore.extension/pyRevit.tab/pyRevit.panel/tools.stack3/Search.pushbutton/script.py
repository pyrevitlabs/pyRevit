from pyrevit.loader import sessionmgr
from pyrevit import forms
from pyrevit import framework
from pyrevit import script


logger = script.get_logger()


class SearchPrompt(forms.WPFWindow):
    def __init__(self, context, width, height, **kwargs):
        forms.WPFWindow.__init__(self, 'SearchPrompt.xaml')
        self.Width = width
        self.MinWidth = self.Width
        self.Height = height

        self._context = sorted(context)
        self.response = None

        self.search_tb.Focus()
        self.hide_element(self.tab_icon)
        self.search_tb.Text = ''
        self.set_search_results()

    def update_results_display(self):
        self.directmatch_tb.Text = ''
        self.wordsmatch_tb.Text = ''

        results = sorted(set(self._search_results))
        res_cout = len(results)

        logger.debug(res_cout)
        logger.debug(results)

        if res_cout > 1:
            self.show_element(self.tab_icon)
        else:
            self.hide_element(self.tab_icon)

        if self._result_index >= res_cout:
            self._result_index = 0

        if self._result_index < 0:
            self._result_index = res_cout - 1

        cur_txt = self.search_tb.Text.lower()

        if not cur_txt:
            self.directmatch_tb.Text = 'pyRevit Search'
            return

        if results:
            cur_res = results[self._result_index]
            logger.debug(cur_res)
            if cur_res.lower().startswith(cur_txt):
                logger.debug('directmatch_tb.Text', cur_res)
                self.directmatch_tb.Text = \
                    self.search_tb.Text + cur_res[len(cur_txt):]
            else:
                logger.debug('wordsmatch_tb.Text', cur_res)
                self.wordsmatch_tb.Text = '- {}'.format(cur_res)

            self.response = cur_res
            return True

        self.response = None
        return False

    def set_search_results(self, *args):
        self._result_index = 0
        self._search_results = []

        for resultset in args:
            self._search_results.extend(resultset)

        self.update_results_display()

    def find_direct_match(self):
        results = []
        cur_txt = self.search_tb.Text.lower()
        if cur_txt:
            for cmd_name in self._context:
                if cmd_name.lower().startswith(cur_txt):
                    results.append(cmd_name)

        return results

    def find_word_match(self):
        results = []
        cur_txt = self.search_tb.Text.lower()
        if cur_txt:
            cur_words = cur_txt.split(' ')
            for cmd_name in self._context:
                if all([x in cmd_name.lower() for x in cur_words]):
                    results.append(cmd_name)

        return results

    def search_txt_changed(self, sender, args):
        dmresults = self.find_direct_match()
        wordresults = self.find_word_match()
        logger.debug(len(dmresults), len(wordresults))
        self.set_search_results(dmresults, wordresults)

    def handle_kb_key(self, sender, args):
        if args.Key == framework.Windows.Input.Key.Escape:
            self.response = None
            self.Close()
        elif args.Key == framework.Windows.Input.Key.Enter:
            self.Close()
        elif args.Key == framework.Windows.Input.Key.Tab \
                or args.Key == framework.Windows.Input.Key.Down:
            self._result_index += 1
            self.update_results_display()
        elif args.Key == framework.Windows.Input.Key.Up:
            self._result_index -= 1
            self.update_results_display()

    @classmethod
    def show_prompt(cls, context, width=300, height=400, **kwargs):
        dlg = cls(context, width, height, **kwargs)
        dlg.ShowDialog()
        return dlg.response

pyrevit_cmds = {}


# find all available commands (for current selection)
# in currently active document
for cmd in sessionmgr.find_all_available_commands():
    cmd_inst = cmd()
    if hasattr(cmd_inst, 'baked_cmdName'):
        pyrevit_cmds[cmd_inst.baked_cmdName] = cmd


selected_cmd_name = SearchPrompt.show_prompt(pyrevit_cmds.keys(),
                                             width=600, height=100)

if selected_cmd_name:
    selected_cmd = pyrevit_cmds[selected_cmd_name]
    sessionmgr.execute_command_cls(selected_cmd)
