"""Loads other types from selected family instance."""

import clr
import os.path as op

from scriptutils import logger, this_script
from scriptutils.userinput import SelectFromList
from revitutils import doc, selection

from Autodesk.Revit.DB import Transaction, Element, Family, FamilySymbol, FamilyInstance
from Autodesk.Revit.UI import TaskDialog


# get family symbol from selection -------------------------------------------------------------------------------------
if not selection.is_empty:
    selected_comp = selection.first
    if isinstance(selected_comp, FamilySymbol):
        logger.debug('Getting family from symbol with id: {}'.format(selected_comp.Id))
        fam_symbol = selected_comp.Family
    elif isinstance(selected_comp, FamilyInstance):
        logger.debug('Getting family from instance with id: {}'.format(selected_comp.Id))
        fam_symbol = selected_comp.Symbol.Family
else:
    TaskDialog.Show('pyRevit', 'At least one family instance must be selected.')
    logger.debug('Cancelled. No elements selected.')
    this_script.exit()

# verify family symbol is ready ----------------------------------------------------------------------------------------
if not fam_symbol:
    logger.error('Can not load family symbol.')
    this_script.exit()
else:
    logger.debug('Family symbol aquired: {}'.format(fam_symbol))

# collect all symbols already loaded -----------------------------------------------------------------------------------
loaded_symbols = set()
for sym_id in fam_symbol.GetFamilySymbolIds():
    fam_sym = doc.GetElement(sym_id)
    loaded_symbols.add(Element.Name.GetValue(fam_sym))

logger.debug('Existing symbols are: {}'.format(loaded_symbols))

# get family document and verify the file exists -----------------------------------------------------------------------
fam_doc = doc.EditFamily(fam_symbol)
fam_doc_path = fam_doc.PathName
if not op.exists(fam_doc_path):
    TaskDialog.Show('pyRevit', 'Can not file original family file at\n{}'.format(fam_doc_path))
    logger.debug('Can not file original family file at {}'.format(fam_doc_path))
    this_script.exit()
else:
    logger.debug('Loading family from: {}'.format(fam_doc_path))


# fake load the family so we can get the symbols -----------------------------------------------------------------------
symbol_list = set()
with Transaction(doc, 'Fake load') as t:
    t.Start()
    # remove existing family so we can load the original
    doc.Delete(fam_symbol.Id)
    # now load the original
    ret_ref = clr.Reference[Family]()
    doc.LoadFamily(fam_doc_path, ret_ref)
    loaded_fam = ret_ref.Value
    # get the symbols from the original
    for sym_id in loaded_fam.GetFamilySymbolIds():
        fam_sym = doc.GetElement(sym_id)
        symbol_list.add(Element.Name.GetValue(fam_sym))
    # okay. we have all the symbols. now rollback all the changes
    t.RollBack()

logger.debug('Original symbols are: {}'.format(symbol_list))

# ask user for required symbol and load into current document
options = sorted(symbol_list - loaded_symbols)
if options:
    selected_symbols = SelectFromList.show(options)
    logger.debug('Selected symbols are: {}'.format(selected_symbols))
    if selected_symbols:
        with Transaction(doc, 'Loaded family type') as t:
            t.Start()
            try:
                for symbol in selected_symbols:
                    logger.debug('Loading symbol: {}'.format(symbol))
                    doc.LoadFamilySymbol(fam_doc_path, symbol)
                t.Commit()
                logger.debug('Successfully loaded all selected symbols')
            except Exception as load_err:
                logger.error('Error loading family symbol: {} from {} | {}'.format(symbol, fam_doc_path, load_err))
                t.RollBack()
else:
    TaskDialog.Show('pyRevit', 'All the family types are already loaded.')
