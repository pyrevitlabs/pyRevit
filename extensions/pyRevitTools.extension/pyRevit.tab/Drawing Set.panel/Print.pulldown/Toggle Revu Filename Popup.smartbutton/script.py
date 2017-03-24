"""Enables and disables the Revu PDF Printer prompt for filename option. The Icon shows the current state of this setting."""

import _winreg as wr

from scriptutils import this_script
from pyrevit.coreutils.ribbon import ICON_MEDIUM

__title__ = 'Toggle\nRevu\nFileName\nPopup'


def get_reg_key():
	return wr.OpenKey(wr.HKEY_CURRENT_USER,r'Software\Bluebeam Software\Brewery\V45\Printer Driver',0,wr.KEY_WRITE)


# noinspection PyUnusedLocal
def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
	on_icon = script_cmp.get_bundle_file('on.png')
	off_icon = script_cmp.get_bundle_file('off.png')

	reg_key = get_reg_key()
	curval = wr.QueryValueEx(reg_key, r'PromptForFileName')
	wr.FlushKey(reg_key)
	reg_key.Close()

	if curval[0] == '1':
		ui_button_cmp.set_icon(on_icon, icon_size=ICON_MEDIUM)
	elif curval[0] == '0':
		ui_button_cmp.set_icon(off_icon, icon_size=ICON_MEDIUM)


def toggleState():
	on_icon = this_script.get_bundle_file('on.png')
	off_icon = this_script.get_bundle_file('off.png')

	reg_key = get_reg_key()
	curval = wr.QueryValueEx(reg_key, r'PromptForFileName')
	if curval[0] == '1':
		wr.SetValueEx(reg_key, r'PromptForFileName', 0, wr.REG_SZ, '0')
		this_script.ui_button.set_icon(off_icon, icon_size=ICON_MEDIUM)
	elif curval[0] == '0':
		wr.SetValueEx(reg_key, r'PromptForFileName', 0, wr.REG_SZ, '1')
		this_script.ui_button.set_icon(on_icon, icon_size=ICON_MEDIUM)
	wr.FlushKey(reg_key)
	reg_key.Close()

if __name__ == '__main__':
	toggleState()
