import re
import os.path as op

from pyrevit import script
from pyrevit.compat import winreg as wr
from pyrevit.coreutils.ribbon import ICON_MEDIUM


logger = script.get_logger()


__context__ = 'zero-doc'
__title__ = 'Revu\nPopup'


__doc__ = 'Enables and disables the Revu PDF Printer prompt for '\
          'filename option. The Icon shows the current state of this setting.'


# op.sep = '\\'
driver_keys = []
BBS_KEY_PATH = r'Software\Bluebeam Software'

BBS_PRINT_DRIVER_MATCH_STR = r'\d{4}\\Brewery\\V\d{2}\\Printer Driver\Z'
logger.debug('Match string is: {}'.format(BBS_PRINT_DRIVER_MATCH_STR))
key_finder = re.compile(BBS_PRINT_DRIVER_MATCH_STR)


def get_reg_key(key, subkey):
    try:
        return wr.OpenKey(key, subkey, 0, wr.KEY_WRITE)
    except Exception as key_error:
        logger.debug('Can not open key: {}'.format(subkey))
        return None


def find_driver_key(driver_keys, parent_string, key):
    subkey_count, value_count, last_changed = wr.QueryInfoKey(key)
    logger.debug('{} reg key has {} subkeys and {} values.'
                 .format(parent_string, subkey_count, value_count))
    for idx in range(0, subkey_count):
        subkey_name = wr.EnumKey(key, idx)
        key_path = op.join(parent_string, subkey_name)

        logger.debug('Checking subkey: {}'.format(key_path))
        dkey = get_reg_key(key, subkey_name)
        if dkey:
            if key_finder.match(key_path):
                logger.debug('Driver key found: {}'.format(key_path))
                driver_keys.append(dkey)

            logger.debug('Looking into subkey for key: {}'.format(key_path))
            find_driver_key(driver_keys, key_path, dkey)


def get_driver_keys():
    global driver_keys

    if not driver_keys:
        logger.debug('Opening master bluebeam registry key: %s' % BBS_KEY_PATH)
        bbs_key = get_reg_key(wr.HKEY_CURRENT_USER, BBS_KEY_PATH)
        if bbs_key:
            logger.debug('Master key acquired.')
            logger.debug('Finding list of printer driver keys.')
            find_driver_key(driver_keys, '', bbs_key)
            return driver_keys
        else:
            return None
    else:
        return driver_keys


def close_keys(dkeys):
    for dkey in dkeys:
        wr.FlushKey(dkey)
        dkey.Close()


def set_filename_prompt_state(dkeys, state):
    if dkeys:
        try:
            for dkey in dkeys:
                wr.SetValueEx(dkey,
                              r'PromptForFileName',
                              0,
                              wr.REG_SZ,
                              '1' if state else '0')
            return state
        except Exception as key_read_err:
            logger.debug('Error accessing registry key value.'
                         ' | {}'.format(key_read_err))
    else:
        logger.debug('No registry keys are available for revu printer driver.')


def query_filename_prompt_state(dkeys):
    state = False
    if dkeys:
        try:
            for dkey in dkeys:
                key_state = wr.QueryValueEx(dkey, r'PromptForFileName')[0]
                logger.debug('Checking reg key state: {}'.format(key_state))
                state |= int(key_state) > 0
            return state
        except Exception as key_read_err:
            logger.debug('Error accessing registry key value.'
                         ' | {}'.format(key_read_err))
    else:
        logger.debug('No registry keys are available for revu printer driver.')


# noinspection PyUnusedLocal
def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    on_icon = script_cmp.get_bundle_file('on.png')
    off_icon = script_cmp.get_bundle_file('off.png')

    dkeys = get_driver_keys()
    if dkeys:
        curval = query_filename_prompt_state(dkeys)
        close_keys(dkeys)

        if curval:
            logger.debug('PDF Printer PromptForFileName is Enabled...')
            ui_button_cmp.set_icon(on_icon, icon_size=ICON_MEDIUM)
        else:
            logger.debug('PDF Printer PromptForFileName is Disabled...')
            ui_button_cmp.set_icon(off_icon, icon_size=ICON_MEDIUM)
        return True
    else:
        return False


def toggle_state():
    dkeys = get_driver_keys()
    if dkeys:
        curval = query_filename_prompt_state(dkeys)

        if curval:
            logger.debug('Prompt For FileName is Enabled. Disabling...')
            set_filename_prompt_state(dkeys, False)
        else:
            logger.debug('Prompt For FileName is Disabled. Enabling...')
            set_filename_prompt_state(dkeys, True)

        script.toggle_icon(not curval)
        close_keys(dkeys)


if __name__ == '__main__':
    toggle_state()
