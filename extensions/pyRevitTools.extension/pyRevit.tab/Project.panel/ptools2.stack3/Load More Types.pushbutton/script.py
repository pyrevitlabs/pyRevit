"""Loads other types from selected family instance."""
#pylint: disable=E0401,C0103
import re
import os.path as op

from pyrevit.framework import clr
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script


logger = script.get_logger()

selection = revit.get_selection()


# get family symbol from selection
family = None
if not selection.is_empty:
    selected_comp = selection.first
    if isinstance(selected_comp, DB.FamilySymbol):
        logger.debug('Getting family from symbol with id: {}'
                     .format(selected_comp.Id))
        family = selected_comp.Family
    elif isinstance(selected_comp, DB.FamilyInstance):
        logger.debug('Getting family from instance with id: {}'
                     .format(selected_comp.Id))
        family = selected_comp.Symbol.Family
    else:
        forms.alert('System families do not have external '
                    'type definition.')
        logger.debug('Cancelled. System families do not have '
                     'external type definition.')
        script.exit()
else:
    forms.alert('At least one family instance must be selected.')
    logger.debug('Cancelled. No elements selected.')
    script.exit()

# verify family symbol is ready
if not family:
    logger.error('Can not load family symbol.')
    script.exit()
else:
    logger.debug('Family symbol aquired: {}'.format(family))


# define a class for family types so they can be smartly sorted
class SmartSortableFamilyType:
    def __init__(self, type_name):
        self.type_name = type_name
        self.sort_alphabetically = False
        self.number_list = [int(x) for x in re.findall(r'\d+', self.type_name)]
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
for sym_id in family.GetFamilySymbolIds():
    family_symbol = revit.doc.GetElement(sym_id)
    family_symbol_name = revit.query.get_name(family_symbol)
    sortable_sym = SmartSortableFamilyType(family_symbol_name)
    logger.debug('Loaded Type: {}'.format(sortable_sym))
    loaded_symbols.add(sortable_sym)


# get family document and verify the file exists
fam_doc = revit.doc.EditFamily(family)
fam_doc_path = fam_doc.PathName
if not op.exists(fam_doc_path):
    forms.alert('Can not find original family file at\n{}'
                .format(fam_doc_path))
    logger.debug('Could not find original family file at {}'
                 .format(fam_doc_path))
    script.exit()
else:
    logger.debug('Loading family from: {}'.format(fam_doc_path))


# fake load the family so we can get the symbols
symbol_list = set()
with revit.DryTransaction('Fake load'):
    # remove existing family so we can load the original
    revit.doc.Delete(family.Id)
    # now load the original
    ret_ref = clr.Reference[DB.Family]()
    revit.doc.LoadFamily(fam_doc_path, ret_ref)
    loaded_fam = ret_ref.Value
    # get the symbols from the original
    for sym_id in loaded_fam.GetFamilySymbolIds():
        family_symbol = revit.doc.GetElement(sym_id)
        family_symbol_name = revit.query.get_name(family_symbol)
        sortable_sym = SmartSortableFamilyType(family_symbol_name)
        logger.debug('Importable Type: {}'.format(sortable_sym))
        symbol_list.add(sortable_sym)
    # okay. we have all the symbols.
    # DryTransaction will rollback all the changes


# ask user for required symbol and load into current document
options = sorted(symbol_list - loaded_symbols)
if options:
    selected_symbols = forms.SelectFromList.show(options, multiselect=True)
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
    forms.alert('All the family types are already loaded.')
