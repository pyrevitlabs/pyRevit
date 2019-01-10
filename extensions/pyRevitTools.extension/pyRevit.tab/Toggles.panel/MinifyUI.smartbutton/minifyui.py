"""Monify UI backend."""
#pylint: disable=E0401,C0103
from pyrevit import forms
from pyrevit import script
from pyrevit.coreutils import ribbon


mlogger = script.get_logger()


MINIFYUI_ENV_VAR = 'MINIFYUIACTIVE'


class TabOption(forms.TemplateListItem):
    def __init__(self, uitab, hidden_tabs_list):
        super(TabOption, self).__init__(uitab)
        self.state = self.name in hidden_tabs_list

    @property
    def name(self):
        return self.item.name


def set_minifyui_config(hidden_tabs_list, config):
    config.hidden_tabs = hidden_tabs_list
    script.save_config()


def get_minifyui_config(config):
    return config.get_option('hidden_tabs', [])


def config_minifyui(config):
    this_ext_name = script.get_extension_name()
    hidden_tabs = get_minifyui_config(config)
    tabs = forms.SelectFromList.show(
        [TabOption(x, hidden_tabs) for x in ribbon.get_current_ui()
         if x.name not in this_ext_name],
        title='Minify UI Config',
        button_name='Hide Selected Tabs in Minified Mode',
        multiselect=True
        )

    if tabs:
        set_minifyui_config([x.name for x in tabs if x], config)


def update_ui(config):
    # Minify or unminify the ui here
    hidden_tabs = get_minifyui_config(config)
    for tab in ribbon.get_current_ui():
        if tab.name in hidden_tabs:
            # not new state since the visible value is reverse
            tab.visible = not script.get_envvar(MINIFYUI_ENV_VAR)


def toggle_minifyui(config):
    new_state = not script.get_envvar(MINIFYUI_ENV_VAR)
    script.set_envvar(MINIFYUI_ENV_VAR, new_state)
    script.toggle_icon(new_state)
    update_ui(config)
