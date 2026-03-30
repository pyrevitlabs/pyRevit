# -*- coding: utf-8 -*-
"""Minify UI backend."""
#pylint: disable=E0401,C0103
import System
from System.Windows import Threading

from pyrevit import forms
from pyrevit import script
from pyrevit import framework
from pyrevit import HOST_APP, UI
from pyrevit.coreutils import ribbon
from pyrevit.runtime import types


mlogger = script.get_logger()


MINIFYUI_ENV_VAR = 'MINIFYUIACTIVE'
MINIFYUI_SUBSCRIBED_ENV_VAR = 'MINIFYUI_SUBSCRIBED'


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
    hidden_tabs = get_minifyui_config(config)
    is_active = script.get_envvar(MINIFYUI_ENV_VAR)
<<<<<<< Updated upstream
    for tab in ribbon.get_current_ui():
        if tab.name in hidden_tabs:
            # not new state since the visible value is reverse
            tab.visible = not is_active


def _deferred_update(config):
    # schedule re-hide after Revit ribbon updates settle
    dispatcher = Threading.Dispatcher.CurrentDispatcher
    def do_update():
        try:
            if script.get_envvar(MINIFYUI_ENV_VAR):
                update_ui(config)
        except Exception as ex:
            mlogger.exception('MinifyUI: deferred update failed: %s', ex)
    action = System.Action(do_update)
    dispatcher.BeginInvoke(
        Threading.DispatcherPriority.Background, action)
    dispatcher.BeginInvoke(
        Threading.DispatcherPriority.ContextIdle, action)
    dispatcher.BeginInvoke(
        Threading.DispatcherPriority.ApplicationIdle, action)


def ensure_subscribed(config):
    # guard: skip if already subscribed
    if script.get_envvar(MINIFYUI_SUBSCRIBED_ENV_VAR):
        return

    uiapp = HOST_APP.uiapp
    if not uiapp:
        return

    def on_view_activated(sender, args):
        try:
            if script.get_envvar(MINIFYUI_ENV_VAR):
                update_ui(config)
                _deferred_update(config)
        except Exception as ex:
            mlogger.debug('MinifyUI: view activation handler failed: %s', ex)

    try:
        handler = framework.EventHandler[
            UI.Events.ViewActivatedEventArgs](on_view_activated)
        uiapp.ViewActivated += handler
        script.set_envvar(MINIFYUI_SUBSCRIBED_ENV_VAR, True)
    except Exception as ex:
        mlogger.warning('MinifyUI: subscribe failed: %s', ex)
=======

    if is_active:
        types.RibbonTabVisibilityUtils.StartHidingTabs(hidden_tabs)
    else:
        types.RibbonTabVisibilityUtils.StopHidingTabs()
>>>>>>> Stashed changes


def toggle_minifyui(config):
    new_state = not script.get_envvar(MINIFYUI_ENV_VAR)
    script.set_envvar(MINIFYUI_ENV_VAR, new_state)
    script.toggle_icon(new_state)
<<<<<<< Updated upstream
    if new_state:
        ensure_subscribed(config)
    update_ui(config)
=======
    update_ui(config)
>>>>>>> Stashed changes
