"""Loads other types from selected family instance."""

import clr
import os.path as op

from scriptutils import logger, this_script
from scriptutils.userinput import SelectFromList
from revitutils import doc, selection

from Autodesk.Revit.DB import Transaction, Element, Family, FamilySymbol, FamilyInstance
from Autodesk.Revit.UI import TaskDialog


# get family symbol from selection
if not selection.is_empty:
    fam_inst = selection.first
    if isinstance(fam_inst, FamilySymbol):
        fam_symbol = fam_inst.Family
    elif isinstance(fam_inst, FamilyInstance):
        fam_symbol = fam_inst.Symbol.Family
else:
    TaskDialog.Show('pyRevit', 'At least one family instance must be selected.')
    this_script.exit()

# verify family symbol is ready
if not fam_symbol:
    logger.error('Can not load family symbol.')
    this_script.exit()

# collect all symbols already loaded
loaded_symbols = set()
for sym_id in fam_symbol.GetFamilySymbolIds():
    fam_sym = doc.GetElement(sym_id)
    loaded_symbols.add(Element.Name.GetValue(fam_sym))

# get family document and verify the file exists
fam_doc = doc.EditFamily(fam_symbol)
fam_doc_path = fam_doc.PathName
if not op.exists(fam_doc_path):
    TaskDialog.Show('pyRevit', 'Can not file original family file at\n{}'.format(fam_doc_path))
    this_script.exit()
else:
    logger.debug('Loading family from: {}'.format(fam_doc_path))


# fake load the family so we can get the types
symbol_list = set()
with Transaction(doc, 'Fake load') as t:
    t.Start()
    ret_ref = clr.Reference[Family]()
    doc.LoadFamily(fam_doc_path, ret_ref)
    loaded_fam = ret_ref.Value
    for sym_id in loaded_fam.GetFamilySymbolIds():
        fam_sym = doc.GetElement(sym_id)
        symbol_list.add(Element.Name.GetValue(fam_sym))
    t.RollBack()

# ask user for required type and load into current document
selected_symbols = SelectFromList.show(sorted(symbol_list - loaded_symbols))
if selected_symbols:
    with Transaction(doc, 'Loaded family type') as t:
        t.Start()
        try:
            for symbol in selected_symbols:
                doc.LoadFamilySymbol(fam_doc_path, symbol)
            t.Commit()
        except Exception as load_err:
            logger.error('Error loading family symbol: {} from {} | {}'.format(symbol, fam_doc_path, load_err))
            t.RollBack()
