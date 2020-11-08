"""Run perflight checks on current model"""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import preflight
from pyrevit import forms
from pyrevit import script

logger = script.get_logger()
output = script.get_output()


def ask_for_preflight_checks():
    # ask user for test case
    selected_checks = forms.SelectFromList.show(
        preflight.get_all_preflight_checks(),
        title='Select Preflight Check(s)',
        button_name='Select Check(s)',
        multiselect=True,
        checked_only=True,
        )

    if selected_checks:
        for check in selected_checks:
            logger.debug('Running: {}'.format(check))
            preflight.run_preflight_check(check, output=output)


if __name__ == "__main__":
    ask_for_preflight_checks()
