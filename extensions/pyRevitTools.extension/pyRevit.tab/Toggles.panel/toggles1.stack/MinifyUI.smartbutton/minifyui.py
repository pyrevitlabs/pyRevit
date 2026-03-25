# -*- coding: utf-8 -*-
"""Minify UI backend.

Hides tabs via pyRevit ribbon wrapper. Persistence across view
switches uses ViewActivated + WPF Dispatcher.BeginInvoke to
schedule re-hides AFTER Revit's ribbon update completes.

No timers, no Idling — pure event-driven.
"""
#pylint: disable=E0401,C0103
import System
from System.Windows import Threading

from pyrevit import forms
from pyrevit import script
from pyrevit import framework
from pyrevit import HOST_APP, UI
from pyrevit.coreutils import ribbon


mlogger = script.get_logger()


MINIFYUI_ENV_VAR = 'MINIFYUIACTIVE'
_VA_HANDLER_ENV = 'MINIFYUI_VA_HANDLER'


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
    """Apply or remove tab visibility."""
    hidden_tabs = get_minifyui_config(config)
    is_active = script.get_envvar(MINIFYUI_ENV_VAR)
    for tab in ribbon.get_current_ui():
        if tab.name in hidden_tabs:
            tab.visible = not is_active


def _deferred_update(config):
    """Schedule update_ui at multiple WPF dispatcher priorities.

    Revit's ribbon updates happen at DataBind/Render priority.
    By scheduling at lower priorities (Background, ContextIdle,
    ApplicationIdle), we run AFTER Revit finishes restoring tabs.

    Multiple priorities ensure we catch updates regardless of
    which WPF pass Revit uses to restore contextual tabs.
    """
    dispatcher = Threading.Dispatcher.CurrentDispatcher

    def do_update():
        try:
            if script.get_envvar(MINIFYUI_ENV_VAR):
                update_ui(config)
        except Exception:
            pass

    action = System.Action(do_update)

    # Schedule at progressively lower priorities to catch
    # ribbon updates at any stage of the WPF dispatcher queue.
    # Background: runs after Render/DataBind
    # ContextIdle: runs when dispatcher is idle
    # ApplicationIdle: last resort, runs when app is fully idle
    dispatcher.BeginInvoke(
        Threading.DispatcherPriority.Background, action)
    dispatcher.BeginInvoke(
        Threading.DispatcherPriority.ContextIdle, action)
    dispatcher.BeginInvoke(
        Threading.DispatcherPriority.ApplicationIdle, action)


def subscribe_handlers(config):
    """Subscribe ViewActivated using HOST_APP.uiapp."""
    unsubscribe_handlers()

    uiapp = HOST_APP.uiapp
    if not uiapp:
        mlogger.warning('MinifyUI: HOST_APP.uiapp is None')
        return

    def on_view_activated(sender, args):
        try:
            if script.get_envvar(MINIFYUI_ENV_VAR):
                # Immediate best-effort hide
                update_ui(config)
                # Deferred re-hides after Revit's ribbon updates
                _deferred_update(config)
        except Exception as ex:
            mlogger.warning('MinifyUI ViewActivated: %s', ex)

    try:
        va_handler = framework.EventHandler[
            UI.Events.ViewActivatedEventArgs](on_view_activated)
        uiapp.ViewActivated += va_handler
        script.set_envvar(_VA_HANDLER_ENV, va_handler)
    except Exception as ex:
        mlogger.warning('MinifyUI: VA sub failed: %s', ex)


def unsubscribe_handlers():
    """Detach ViewActivated handler."""
    uiapp = HOST_APP.uiapp
    if not uiapp:
        return

    old_va = script.get_envvar(_VA_HANDLER_ENV)
    if old_va:
        try:
            uiapp.ViewActivated -= old_va
        except Exception:
            pass
        script.set_envvar(_VA_HANDLER_ENV, None)


def toggle_minifyui(config):
    new_state = not script.get_envvar(MINIFYUI_ENV_VAR)
    script.set_envvar(MINIFYUI_ENV_VAR, new_state)
    script.toggle_icon(new_state)

    if new_state:
        subscribe_handlers(config)
        update_ui(config)
    else:
        update_ui(config)
        unsubscribe_handlers()


def dump_ribbon_info():
    """Diagnostic: Ctrl+Click the MinifyUI button."""
    output = script.get_output()
    output.print_md('## MinifyUI Ribbon Diagnostic')

    output.print_md('### Ribbon Tabs')
    cfg = get_minifyui_config(script.get_config())
    for tab in ribbon.get_current_ui():
        marker = ''
        if tab.name in cfg:
            marker = ' **[HIDDEN]**' if not tab.visible \
                else ' **[SHOULD BE HIDDEN]**'
        output.print_md(
            '- `{}` visible={}{}'.format(tab.name, tab.visible, marker))

    output.print_md('### Handler State')
    output.print_md('- MINIFYUIACTIVE = `{}`'.format(
        script.get_envvar(MINIFYUI_ENV_VAR)))
    output.print_md('- HOST_APP.uiapp = `{}`'.format(
        'SET' if HOST_APP.uiapp else 'None'))
    output.print_md('- VA_HANDLER = `{}`'.format(
        'SET' if script.get_envvar(_VA_HANDLER_ENV) else 'None'))
