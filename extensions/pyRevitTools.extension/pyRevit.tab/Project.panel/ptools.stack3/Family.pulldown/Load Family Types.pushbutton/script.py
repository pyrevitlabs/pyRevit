"""Loads other types from selected family instance."""

import re
import os.path as op

from pyrevit.framework import clr
from pyrevit import forms
from pyrevit import revit, DB, UI
from pyrevit import script


logger = script.get_logger()

selection = revit.get_selection()


# get family symbol from selection
fam_symbol = None
if not selection.is_empty:
    selected_comp = selection.first
    if isinstance(selected_comp, DB.FamilySymbol):
        logger.debug('Getting family from symbol with id: {}'
                     .format(selected_comp.Id))
        fam_symbol = selected_comp.Family
    elif isinstance(selected_comp, DB.FamilyInstance):
        logger.debug('Getting family from instance with id: {}'
                     .format(selected_comp.Id))
        fam_symbol = selected_comp.Symbol.Family
    else:
        UI.TaskDialog.Show('pyRevit',
                           'System families do not have external '
                           'type definition.')
        logger.debug('Cancelled. System families do not have '
                     'external type definition.')
        script.exit()
else:
    UI.TaskDialog.Show('pyRevit',
                       'At least one family instance must be selected.')
    logger.debug('Cancelled. No elements selected.')
    script.exit()

# verify family symbol is ready
if not fam_symbol:
    logger.error('Can not load family symbol.')
    script.exit()
else:
    logger.debug('Family symbol aquired: {}'.format(fam_symbol))


# define a class for family types so they can be smartly sorted
class SmartSortableFamilyType:
    def __init__(self, type_name):
        self.type_name = type_name
        self.sort_alphabetically = False
        self.number_list = [int(x) for x in re.findall('\d+', self.type_name)]
        if not self.number_list:
            self.sort_alphabetically = True

    def __str__(self):
        return self.type_name

    def __repr__(self):
        return '<SmartSortableFamilyType Name:{} Values:{} StringSort:{}>'\
               .format(self.type_name,
                       self.number_list,
                       self.sort_alphabetically)

    def __eq__(self, other):
        return self.type_name == other.type_name

    def __hash__(self):
        return hash(self.type_name)

    def __lt__(self, other):
        if self.sort_alphabetically or other.sort_alphabetically:
            return self.type_name < other.type_name
        else:
            return self.number_list < other.number_list


# collect all symbols already loaded
loaded_symbols = set()
for sym_id in fam_symbol.GetFamilySymbolIds():
    fam_sym = revit.doc.GetElement(sym_id)
    fam_sym_name = revit.ElementWrapper(fam_sym).name
    sortable_sym = SmartSortableFamilyType(fam_sym_name)
    logger.debug('Loaded Type: {}'.format(sortable_sym))
    loaded_symbols.add(sortable_sym)


# get family document and verify the file exists
fam_doc = revit.doc.EditFamily(fam_symbol)
fam_doc_path = fam_doc.PathName
if not op.exists(fam_doc_path):
    UI.TaskDialog.Show('pyRevit',
                       'Can not file original family file at\n{}'
                       .format(fam_doc_path))
    logger.debug('Can not file original family file at {}'
                 .format(fam_doc_path))
    script.exit()
else:
    logger.debug('Loading family from: {}'.format(fam_doc_path))


# fake load the family so we can get the symbols
symbol_list = set()
with revit.DryTransaction('Fake load'):
    # remove existing family so we can load the original
    revit.doc.Delete(fam_symbol.Id)
    # now load the original
    ret_ref = clr.Reference[DB.Family]()
    revit.doc.LoadFamily(fam_doc_path, ret_ref)
    loaded_fam = ret_ref.Value
    # get the symbols from the original
    for sym_id in loaded_fam.GetFamilySymbolIds():
        fam_sym = revit.doc.GetElement(sym_id)
        fam_sym_name = revit.ElementWrapper(fam_sym).name
        sortable_sym = SmartSortableFamilyType(fam_sym_name)
        logger.debug('Importable Type: {}'.format(sortable_sym))
        symbol_list.add(sortable_sym)
    # okay. we have all the symbols.
    # DryTransaction will rollback all the changes


# ask user for required symbol and load into current document
options = sorted(symbol_list - loaded_symbols)
if options:
    selected_symbols = forms.SelectFromList.show(options)
    logger.debug('Selected symbols are: {}'.format(selected_symbols))
    if selected_symbols:
        with revit.Transaction('Loaded family type'):
            try:
                for symbol in selected_symbols:
                    logger.debug('Loading symbol: {}'.format(symbol))
                    revit.doc.LoadFamilySymbol(fam_doc_path, symbol.type_name)
                logger.debug('Successfully loaded all selected symbols')
            except Exception as load_err:
                logger.error('Error loading family symbol from {} | {}'
                             .format(fam_doc_path, load_err))
                raise load_err
else:
    UI.TaskDialog.Show('pyRevit',
                       'All the family types are already loaded.')
