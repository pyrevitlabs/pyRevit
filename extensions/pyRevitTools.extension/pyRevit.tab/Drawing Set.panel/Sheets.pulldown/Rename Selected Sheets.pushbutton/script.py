"""Rename selected sheet names in batch."""

from pyrevit import revit, DB
from pyrevit import forms


RENAME_MODES = [
    'Find & Replace',
    'Add Prefix',
    'Add Suffix',
    'to UPPERCASE',
    'to lowercase',
]


def _get_sheet_name(sheet):
    return sheet.Parameter[DB.BuiltInParameter.SHEET_NAME].AsString()


def _set_sheet_name(sheet, name):
    sheet.Parameter[DB.BuiltInParameter.SHEET_NAME].Set(name)


def _collect_rename_inputs(mode):
    if mode == 'Find & Replace':
        find_txt = forms.ask_for_string(
            prompt='Find text in current sheet names:',
            title='Rename Selected Sheets'
            )
        if find_txt is None:
            return None
        if find_txt == '':
            forms.alert('Find text cannot be empty.')
            return None
        replace_txt = forms.ask_for_string(
            default='',
            prompt='Replace with:',
            title='Rename Selected Sheets'
            )
        if replace_txt is None:
            return None
        return {'find': find_txt, 'replace': replace_txt}

    if mode == 'Add Prefix':
        prefix_txt = forms.ask_for_string(
            default='',
            prompt='Prefix to add to selected sheet names:',
            title='Rename Selected Sheets'
            )
        if prefix_txt is None:
            return None
        if prefix_txt == '':
            forms.alert('Prefix cannot be empty.')
            return None
        return {'prefix': prefix_txt}

    if mode == 'Add Suffix':
        suffix_txt = forms.ask_for_string(
            default='',
            prompt='Suffix to add to selected sheet names:',
            title='Rename Selected Sheets'
            )
        if suffix_txt is None:
            return None
        if suffix_txt == '':
            forms.alert('Suffix cannot be empty.')
            return None
        return {'suffix': suffix_txt}

    return {}


def _build_new_name(old_name, mode, data):
    if mode == 'Find & Replace':
        return old_name.replace(data['find'], data['replace'])
    if mode == 'Add Prefix':
        return '{}{}'.format(data['prefix'], old_name)
    if mode == 'Add Suffix':
        return '{}{}'.format(old_name, data['suffix'])
    if mode == 'to UPPERCASE':
        return old_name.upper()
    if mode == 'to lowercase':
        return old_name.lower()
    return old_name


def _print_preview(rename_pairs):
    print('Rename preview:')
    for idx, pair in enumerate(rename_pairs):
        if idx >= 25:
            print('... and {} more'.format(len(rename_pairs) - 25))
            break
        print('[{}] {} -> {}'.format(
            pair['sheet'].SheetNumber,
            pair['old_name'],
            pair['new_name']
            ))


def _report_results(renamed, unchanged, conflicts, failed):
    print('Rename Selected Sheets results')
    print('  Renamed: {}'.format(len(renamed)))
    print('  Unchanged: {}'.format(len(unchanged)))
    print('  Conflicts skipped: {}'.format(len(conflicts)))
    print('  Failed: {}'.format(len(failed)))
    if renamed:
        print('\nRenamed sheets:')
        for item in renamed:
            print('  [{}] {} -> {}'.format(
                item['sheet_number'],
                item['old_name'],
                item['new_name']
                ))
    if conflicts:
        print('\nSkipped because target name was not unique:')
        for item in conflicts:
            print('  [{}] {} -> {} ({})'.format(
                item['sheet_number'],
                item['old_name'],
                item['new_name'],
                item['reason']
                ))
    if failed:
        print('\nFailed to rename:')
        for item in failed:
            print('  [{}] {} -> {} ({})'.format(
                item['sheet_number'],
                item['old_name'],
                item['new_name'],
                item['reason']
                ))


def _execute_renames(rename_pairs):
    renamed = []
    failed = []
    temp_name_map = {}

    with revit.Transaction('Rename Selected Sheets'):
        for idx, pair in enumerate(rename_pairs):
            sheet = pair['sheet']
            temp_name = '__pyrevit_temp_sheet_name_{}_{}__'.format(
                sheet.Id.IntegerValue,
                idx
                )
            try:
                _set_sheet_name(sheet, temp_name)
                temp_name_map[sheet.Id.IntegerValue] = temp_name
            except Exception as err:
                failed.append({
                    'sheet_number': pair['sheet'].SheetNumber,
                    'old_name': pair['old_name'],
                    'new_name': pair['new_name'],
                    'reason': 'Could not assign temporary name: {}'.format(err),
                })

        for pair in rename_pairs:
            sheet = pair['sheet']
            if sheet.Id.IntegerValue not in temp_name_map:
                continue
            try:
                _set_sheet_name(sheet, pair['new_name'])
                renamed.append({
                    'sheet_number': pair['sheet'].SheetNumber,
                    'old_name': pair['old_name'],
                    'new_name': pair['new_name'],
                })
            except Exception as err:
                restore_reason = ''
                try:
                    _set_sheet_name(sheet, pair['old_name'])
                    restore_reason = ' Restored original name.'
                except Exception as restore_err:
                    temp_name = temp_name_map[sheet.Id.IntegerValue]
                    try:
                        _set_sheet_name(sheet, temp_name)
                        restore_reason = (
                            ' Could not restore original name: {}. '
                            'Sheet was kept on temporary name: {}.'
                            .format(restore_err, temp_name)
                        )
                    except Exception as temp_restore_err:
                        restore_reason = (
                            ' Could not restore original name: {}. '
                            'Could not restore temporary name {} either: {}.'
                            .format(restore_err, temp_name, temp_restore_err)
                        )
                failed.append({
                    'sheet_number': pair['sheet'].SheetNumber,
                    'old_name': pair['old_name'],
                    'new_name': pair['new_name'],
                    'reason': 'Could not assign target name: {}.{}'.format(
                        err,
                        restore_reason
                    ),
                })

    return renamed, failed


def main():
    selected_sheets = forms.select_sheets(title='Select Sheets', use_selection=True)
    if not selected_sheets:
        return

    selected_option, switches = forms.CommandSwitchWindow.show(
        RENAME_MODES,
        switches=['Show Report'],
        message='Select rename option:'
        )
    if not selected_option:
        return

    rename_inputs = _collect_rename_inputs(selected_option)
    if rename_inputs is None:
        return

    all_sheet_names = {}
    all_sheets = DB.FilteredElementCollector(revit.doc) \
                   .OfClass(DB.ViewSheet) \
                   .WhereElementIsNotElementType() \
                   .ToElements()
    for sheet in all_sheets:
        all_sheet_names[sheet.Id.IntegerValue] = _get_sheet_name(sheet)

    rename_pairs = []
    unchanged = []
    for sheet in selected_sheets:
        old_name = _get_sheet_name(sheet)
        new_name = _build_new_name(old_name, selected_option, rename_inputs)
        if old_name == new_name:
            unchanged.append({
                'sheet_number': sheet.SheetNumber,
                'old_name': old_name,
                'new_name': new_name,
            })
            continue
        rename_pairs.append({
            'sheet': sheet,
            'old_name': old_name,
            'new_name': new_name,
        })

    if not rename_pairs:
        forms.alert('No sheet names changed with selected option.')
        if switches['Show Report']:
            _report_results([], unchanged, [], [])
        return

    conflicts = []
    valid_pairs = []
    target_names = {}
    for pair in rename_pairs:
        target_name = pair['new_name']
        target_names.setdefault(target_name, []).append(pair)

    for tname, pairs in target_names.items():
        if len(pairs) > 1:
            for pair in pairs:
                conflicts.append({
                    'sheet_number': pair['sheet'].SheetNumber,
                    'old_name': pair['old_name'],
                    'new_name': pair['new_name'],
                    'reason': 'Target name is repeated in selected sheets',
                })
        else:
            valid_pairs.append(pairs[0])

    unique_pairs = list(valid_pairs)
    while True:
        selected_sheet_ids = set([x['sheet'].Id.IntegerValue for x in unique_pairs])
        existing_names = set(
            name for sid, name in all_sheet_names.items()
            if sid not in selected_sheet_ids
        )

        next_unique_pairs = []
        removed_any = False
        for pair in unique_pairs:
            if pair['new_name'] in existing_names:
                conflicts.append({
                    'sheet_number': pair['sheet'].SheetNumber,
                    'old_name': pair['old_name'],
                    'new_name': pair['new_name'],
                    'reason': 'Target name already exists in model',
                })
                removed_any = True
            else:
                next_unique_pairs.append(pair)

        unique_pairs = next_unique_pairs
        if not removed_any:
            break

    if not unique_pairs:
        forms.alert('No valid unique target names. Nothing renamed.')
        _report_results([], unchanged, conflicts, [])
        return

    _print_preview(unique_pairs)
    proceed = forms.alert(
        'Rename {} selected sheets?\n'
        '{} sheets are ready to rename.\n'
        '{} sheets will be skipped because of conflicts.\n'
        'See output window for preview.'.format(
            len(selected_sheets),
            len(unique_pairs),
            len(conflicts)
            ),
        title='Rename Selected Sheets',
        yes=True,
        no=True,
        ok=False
        )
    if not proceed:
        return

    renamed, failed = _execute_renames(unique_pairs)

    if switches['Show Report'] or conflicts or failed:
        _report_results(renamed, unchanged, conflicts, failed)
    forms.alert(
        'Done.\nRenamed: {}\nSkipped (unchanged/conflicts): {}\nFailed: {}'.format(
            len(renamed),
            len(unchanged) + len(conflicts),
            len(failed)
            ),
        title='Rename Selected Sheets'
        )


main()
