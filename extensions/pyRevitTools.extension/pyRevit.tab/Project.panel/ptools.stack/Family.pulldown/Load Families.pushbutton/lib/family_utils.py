"""Module to load Family into project"""

# pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import os
import re

from pyrevit import forms, revit, DB, script

logger = script.get_logger()


def get_family_name(path):
    """Name Revit gives to the family loaded from the given file.

    Args:
        path (str): absolute path to the family .rfa file

    Returns:
        str: file name without the .rfa extension
    """
    return os.path.splitext(os.path.basename(path))[0]


def get_loaded_family_names(doc=None):
    """Names of the families that are already in the project.

    Collects once, so a whole selection can be checked without running a
    collector per family.

    Args:
        doc (DB.Document, optional): defaults to the active document

    Returns:
        set[str]: family names, to be compared against get_family_name
    """
    doc = doc or revit.doc
    collector = DB.FilteredElementCollector(doc).OfClass(DB.Family)
    return {family.Name for family in collector}


class FamilyLoader:
    """
    Enables loading a family from an absolute path.

    Attributes
    ----------
    path : str
        Absolute path to family .rfa file
    name : str
        File name
    overwrite : bool
        Overwrite a family of the same name that is already in the project
    is_loaded : bool
        Checks if family name already exists in project

    Methods
    -------
    get_symbols()
        Loads family in a fake transaction to return all symbols
    load_selective()
        Loads the family and selected symbols, returns whether it worked
    load_all()
        Loads family and all its symbols, returns whether it worked

    Credit
    ------
    Based on Ehsan Iran-Nejads 'Load More Types'
    """

    def __init__(self, path, overwrite=False):
        """
        Parameters
        ----------
        path : str
            Absolute path to family .rfa file
        overwrite : bool, optional
            If True, a family already present in the project is replaced by
            the one on disk and its parameter values are overwritten.
            If False, Revit refuses to reload an existing family.
        """
        self.path = path
        self.name = get_family_name(path)
        self.overwrite = overwrite

    def _load_family(self):
        """Loads the whole family, honoring self.overwrite.

        Returns:
            bool: False if Revit refused the file, e.g. because the family
                is already in the project and overwriting is disabled.
        """
        if not self.overwrite:
            return revit.doc.LoadFamily(self.path)
        loaded, _ = revit.create.load_family_with_result(self.path)
        return loaded

    def _load_symbol(self, symbol_name):
        """Loads a single family symbol, honoring self.overwrite.

        Args:
            symbol_name (str): name of the family type to load

        Returns:
            bool: False if Revit refused the type
        """
        if not self.overwrite:
            return revit.doc.LoadFamilySymbol(self.path, symbol_name)
        return revit.create.load_family_symbol(self.path, symbol_name)

    @property
    def is_loaded(self):
        """
        Checks if family name already exists in project

        Returns
        -------
        bool
            Flag indicating if family is already loaded
        """
        return self.name in get_loaded_family_names()

    def get_symbols(self):
        """
        Loads family in a fake transaction to return all symbols.

        Returns
        -------
        set()
            Set of family symbols

        Remark
        ------
        Uses SmartSortableFamilySymbol for effective sorting
        """
        logger.debug("Fake loading family: {}".format(self.name))
        symbol_set = set()
        with revit.ErrorSwallower():
            # DryTransaction will rollback all the changes
            with revit.DryTransaction("Fake load"):
                for symbol in revit.create.load_family(self.path):
                    symbol_name = revit.query.get_name(symbol)
                    sortable_sym = SmartSortableFamilySymbol(symbol_name)
                    logger.debug("Importable Symbol: {}".format(sortable_sym))
                    symbol_set.add(sortable_sym)
        return sorted(symbol_set)

    def load_selective(self):
        """Loads the family and selected symbols.

        Returns:
            bool: False if the user cancelled the type selection, or if
                Revit refused any of the selected types. The family is
                left untouched in the first case, partially loaded in the
                second.
        """
        symbols = self.get_symbols()

        # Dont prompt if only 1 symbol available
        if len(symbols) == 1:
            return self.load_all()

        # User input -> Select family symbols
        selected_symbols = forms.SelectFromList.show(
            symbols, title=self.name, button_name="Load type(s)", multiselect=True
        )
        if not selected_symbols:
            logger.debug("No family symbols selected.")
            return False
        logger.debug("Selected symbols are: {}".format(selected_symbols))

        # Load family with selected symbols
        with revit.Transaction("Loaded {}".format(self.name)):
            try:
                loaded = True
                for symbol in selected_symbols:
                    logger.debug("Loading symbol: {}".format(symbol))
                    if not self._load_symbol(symbol.symbol_name):
                        logger.error(
                            "Revit refused to load symbol {} from {}".format(
                                symbol, self.path
                            )
                        )
                        loaded = False
                return loaded
            except Exception as load_err:
                logger.error(
                    "Error loading family symbol from {} | {}".format(
                        self.path, load_err
                    )
                )
                raise load_err

    def load_all(self):
        """Loads family and all its symbols.

        Returns:
            bool: False if Revit refused the file
        """
        with revit.Transaction("Loaded {}".format(self.name)):
            try:
                if not self._load_family():
                    logger.error(
                        "Revit refused to load family from {}".format(self.path)
                    )
                    return False
                logger.debug("Successfully loaded family: {}".format(self.name))
                return True
            except Exception as load_err:
                logger.error(
                    "Error loading family symbol from {} | {}".format(
                        self.path, load_err
                    )
                )
                raise load_err


class SmartSortableFamilySymbol:
    """
    Enables smart sorting of family symbols.

    Attributes
    ----------
    symbol_name : str
        name of the family symbol

    Example
    -------
    symbol_set = set()
    for family_symbol in familiy_symbols:
        family_symbol_name = revit.query.get_name(family_symbol)
        sortable_sym = SmartSortableFamilySymbol(family_symbol_name)
        symbol_set.add(sortable_sym)
    sorted_symbols = sorted(symbol_set)

    Credit
    ------
    Copied from Ehsan Iran-Nejads SmartSortableFamilyType
    in 'Load More Types'.
    """

    def __init__(self, symbol_name):
        self.symbol_name = symbol_name
        self.sort_alphabetically = False
        self.number_list = [int(x) for x in re.findall(r"\d+", self.symbol_name)]
        if not self.number_list:
            self.sort_alphabetically = True

    def __str__(self):
        return self.symbol_name

    def __repr__(self):
        return "<SmartSortableFamilySymbol Name:{} Values:{} StringSort:{}>".format(
            self.symbol_name, self.number_list, self.sort_alphabetically
        )

    def __eq__(self, other):
        return self.symbol_name == other.symbol_name

    def __hash__(self):
        return hash(self.symbol_name)

    def __lt__(self, other):
        if self.sort_alphabetically or other.sort_alphabetically:
            return self.symbol_name < other.symbol_name
        else:
            return self.number_list < other.number_list
