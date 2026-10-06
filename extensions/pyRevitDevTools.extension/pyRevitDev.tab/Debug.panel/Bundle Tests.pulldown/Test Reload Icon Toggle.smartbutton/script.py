"""Test SmartButton icon persistence across reloads inside pulldowns.

Mirrors the Update.smartbutton pattern: __selfinit__ applies the orange dot
icon only when the stored state is on, and leaves the loader-applied default
icon otherwise. Click the button to toggle the state; it is stored in the
user config ini so it can be inspected while troubleshooting.

After a reload the icon must match the stored state: orange when on, the
default bundle icon when off. A mismatch means __selfinit__ was not re-run
(default shown while state is on) or the loader failed to restore the bundle
icon (orange shown while state is off).
"""
#pylint: disable=C0103,E0401
from pyrevit import script
from pyrevit.coreutils.ribbon import ICON_MEDIUM

CONFIG_SECTION = 'devtools_reload_tests'
STATE_OPTION = 'pulldown_state'


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    # apply the stored state; the loader is responsible for restoring the
    # default bundle icon when the state is off
    config = script.get_config(CONFIG_SECTION)
    if config.get_option(STATE_OPTION, default_value=False):
        icon = script_cmp.get_bundle_file('on.png')
        ui_button_cmp.set_icon(icon, icon_size=ICON_MEDIUM)
    return True


if __name__ == '__main__':
    from pyrevit.userconfig import user_config

    config = script.get_config(CONFIG_SECTION)
    state = not config.get_option(STATE_OPTION, default_value=False)
    config.set_option(STATE_OPTION, state)
    script.save_config()
    # the default bundle icon stands in for the off state so the click
    # result matches what a reload would show
    script.toggle_icon(state, off_icon_path=script.get_bundle_file('icon.png'))

    print('Config file: {}'.format(user_config.config_file))
    print('[{}] {} = {}'.format(CONFIG_SECTION, STATE_OPTION, state))
    print('Icon should now be {} and must stay that way after a reload.'
          .format('the orange dot' if state else 'the default bundle icon'))
