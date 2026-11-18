from pyrevit import script

CONFIG_SECTION = "devtools_checkbox_tests"
STATE_OPTION = "test_stack_shoulder_state"


def __chk_init__(ctx):
    config = script.get_config(CONFIG_SECTION)
    ctx.is_checked = bool(config.get_option(STATE_OPTION, default_value=ctx.is_checked))


def __chk_on_change__(sender, args, ctx):
    config = script.get_config(CONFIG_SECTION)
    config.set_option(STATE_OPTION, ctx.is_checked)
    script.save_config()
