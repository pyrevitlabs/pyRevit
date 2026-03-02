"""
Interop helpers for Revit IFC export.

This module:
- Loads the IFC.Net assembly to provide IFC schema types (e.g. Ifc4).
- Parses Revit IFC exporter JSON configuration files and maps them to
  Autodesk.Revit.DB.IFCExportOptions.
- Exposes high-level helpers (e.g. IFCExporter) around Document.Export
  for IFC exports.
"""
import os.path as op
import json
import codecs
from pyrevit import clr, BIN_DIR, DB
from pyrevit.coreutils.logger import get_logger

clr.AddReferenceToFileAndPath(op.join(BIN_DIR, "Ifc.Net"))

import Ifc4

mlogger = get_logger(__name__)

# ---------------------------------------------------------------------------
# IFCVersion integer -> enum mapping
# (values match what Revit writes into the JSON "IFCVersion" field)
# ---------------------------------------------------------------------------
IFC_VERSION_MAP = {int(v): v for v in DB.IFCVersion.GetValues(DB.IFCVersion)}

# ---------------------------------------------------------------------------
# Keys that map directly to IFCExportOptions *properties* (not AddOption)
# ---------------------------------------------------------------------------
DIRECT_PROPERTY_KEYS = {
    "SpaceBoundaries",  # -> SpaceBoundaryLevel  (int)
    "SplitWallsAndColumns",  # -> WallAndColumnSplitting  (bool)
    "ExportBaseQuantities",  # -> ExportBaseQuantities  (bool)
    "ExportUserDefinedParameterMappingFileName",  # -> FamilyMappingFile  (str)
}

# ---------------------------------------------------------------------------
# Keys that require special handling and must NOT be forwarded to AddOption
# ---------------------------------------------------------------------------
SKIP_ADDOPTION_KEYS = DIRECT_PROPERTY_KEYS | {
    "IFCVersion",  # handled via FileVersion property
    "Name",  # config metadata only
    "ActivePhaseId",  # setting phase can cause unknown Revit errors
    "IFCFileType",  # file extension, not an export option
    "ExchangeRequirement",  # schema concept, not directly an export option
    "ClassificationSettings",  # nested dict - handled separately
    "ProjectAddress",  # nested dict - handled separately
}


def _bool_str(value):
    """Convert a Python bool to the 'True'/'False' string Revit expects."""
    return "True" if value else "False"


def _tessellation_str(value):
    """
    Revit bug workaround: TessellationLevelOfDetail must be passed with a
    comma as the decimal separator (e.g. '0,5' instead of '0.5').
    """
    return str(float(value)).replace(".", ",")


def load_config(config_path):
    """
    Load a Revit IFC configuration JSON file.

    Parameters
    ----------
    config_path : str
        Absolute path to the .json file exported by Revit's IFC exporter.

    Returns
    -------
    dict
        Parsed configuration dictionary.

    Raises
    ------
    IOError  : if the file does not exist.
    ValueError : if the file is not valid JSON.
    """
    if not op.isfile(config_path):
        raise IOError("IFC config file not found: {}".format(config_path))
    with codecs.open(config_path, "r", "utf-8") as fh:
        try:
            return json.load(fh)
        except ValueError as exc:
            raise ValueError(
                "Failed to parse IFC config JSON '{}': {}".format(config_path, exc)
            )


def build_export_options(
    config=None, overrides=None, filter_view_id=None
):
    """
    Build an IFCExportOptions object from a config dict and/or keyword overrides.

    Parameters
    ----------
    config : dict, optional
        Parsed JSON config (from load_config or a hand-crafted dict).
    overrides : dict, optional
        Key/value pairs that override or supplement config values.
        Accepts the same keys as the JSON config file.
    filter_view_id : Autodesk.Revit.DB.ElementId, optional
        If provided, only elements visible in this view are exported.

    Returns
    -------
    Autodesk.Revit.DB.IFCExportOptions
    """
    cfg = {}
    if config:
        cfg.update(config)
    if overrides:
        cfg.update(overrides)

    options = DB.IFCExportOptions()

    # -- IFC Version --------------------------------------------------------
    ifc_version_int = cfg.get("IFCVersion", 0)
    ifc_version_enum = IFC_VERSION_MAP.get(ifc_version_int, DB.IFCVersion.Default)
    options.FileVersion = ifc_version_enum
    mlogger.debug("IFCVersion       : {} ({})".format(ifc_version_int, ifc_version_enum))

    # -- Direct properties --------------------------------------------------
    options.SpaceBoundaryLevel = int(cfg.get("SpaceBoundaries", 0))
    options.WallAndColumnSplitting = bool(cfg.get("SplitWallsAndColumns", False))
    options.ExportBaseQuantities = bool(cfg.get("ExportBaseQuantities", False))

    mapping_file = cfg.get("ExportUserDefinedParameterMappingFileName", "")
    if mapping_file:
        options.FamilyMappingFile = mapping_file

    # -- Filter view --------------------------------------------------------
    if filter_view_id is not None:
        options.FilterViewId = filter_view_id

    # -- AddOption keys -----------------------------------------------------
    # Booleans
    bool_keys = [
        "IncludeSteelElements",
        "Export2DElements",
        "ExportRoomsInView",
        "ExportInternalRevitPropertySets",
        "ExportIFCCommonPropertySets",
        "ExportMaterialPsets",
        "ExportSchedulesAsPsets",
        "ExportSpecificSchedules",
        "ExportUserDefinedPsets",
        "ExportUserDefinedParameterMapping",
        "ExportPartsAsBuildingElements",
        "ExportSolidModelRep",
        "UseActiveViewGeometry",
        "UseFamilyAndTypeNameForReference",
        "Use2DRoomBoundaryForVolume",
        "IncludeSiteElevation",
        "StoreIFCGUID",
        "ExportBoundingBox",
        "UseOnlyTriangulation",
        "UseTypeNameOnlyForIfcType",
        "UseVisibleRevitNameAsEntityName",
        "VisibleElementsOfCurrentView",
    ]
    for key in bool_keys:
        if key in cfg:
            val = _bool_str(cfg[key])
            options.AddOption(key, val)
            mlogger.debug("{:45s}: {}".format(key, val))

    # Integer / string keys
    int_str_keys = [
        "ExportLinkedFiles",
        "SitePlacement",
        "SpaceBoundaries",  # also passed as AddOption for the IFC exporter plugin
    ]
    for key in int_str_keys:
        if key in cfg:
            val = str(cfg[key])
            options.AddOption(key, val)
            mlogger.debug("{:45s}: {}".format(key, val))

    # String-only keys
    str_keys = [
        "ExportUserDefinedPsetsFileName",
        "ExcludeFilter",
        "GeoRefCRSName",
        "GeoRefCRSDesc",
        "GeoRefEPSGCode",
        "GeoRefGeodeticDatum",
        "GeoRefMapUnit",
        "SelectedSite",
        "COBieCompanyInfo",
        "COBieProjectInfo",
    ]
    for key in str_keys:
        if key in cfg:
            val = cfg[key] or ""
            options.AddOption(key, val)
            mlogger.debug("{:45s}: {}".format(key, val))

    # -- Tessellation (comma bug workaround) --------------------------------
    if "TessellationLevelOfDetail" in cfg:
        raw = cfg["TessellationLevelOfDetail"]
        val = _tessellation_str(raw)
        options.AddOption("TessellationLevelOfDetail", val)
        mlogger.debug(
            "{:45s}: {} (raw={}, comma-separated)".format(
                "TessellationLevelOfDetail", val, raw
            )
        )

    # -- Nested: ProjectAddress ---------------------------------------------
    pa = cfg.get("ProjectAddress", {})
    if pa:
        options.AddOption(
            "UpdateProjectInformation",
            _bool_str(pa.get("UpdateProjectInformation", False)),
        )
        options.AddOption(
            "AssignAddressToSite", _bool_str(pa.get("AssignAddressToSite", False))
        )
        options.AddOption(
            "AssignAddressToBuilding",
            _bool_str(pa.get("AssignAddressToBuilding", True)),
        )

    # -- Nested: ClassificationSettings ------------------------------------
    cs = cfg.get("ClassificationSettings", {})
    if cs:
        for sub_key in [
            "ClassificationName",
            "ClassificationEdition",
            "ClassificationSource",
            "ClassificationLocation",
            "ClassificationFieldName",
        ]:
            val = cs.get(sub_key) or ""
            if val:
                options.AddOption(sub_key, val)

    return options


class IFCExporter(object):
    """
    High-level wrapper around Revit's Document.Export IFC pipeline.

    Parameters
    ----------
    doc : Autodesk.Revit.DB.Document
        The active Revit document.
    """

    def __init__(self, doc):
        self.doc = doc

    def export(
        self,
        folder,
        filename,
        config_path=None,
        overrides=None,
        filter_view_id=None,
    ):
        """
        Export the document to IFC.

        Parameters
        ----------
        folder : str
            Output directory.
        filename : str
            Output file name, e.g. 'MyModel.ifc'.
        config_path : str, optional
            Path to a Revit IFC JSON configuration file.
        overrides : dict, optional
            Option keys to override (or supplement) the config file.
        filter_view_id : Autodesk.Revit.DB.ElementId, optional
            View to use for visibility-based filtering.

        Returns
        -------
        bool
            True if Revit reported success.

        Raises
        ------
        IOError   : if config_path is given but the file is missing.
        Exception : re-raises any Revit API error.
        """
        config = {}
        if config_path:
            config = load_config(config_path)
            mlogger.debug("Loaded IFC config: {}".format(config_path))

        mlogger.debug("Building IFCExportOptions ...")

        export_options = build_export_options(
            config=config,
            overrides=overrides,
            filter_view_id=filter_view_id,
        )

        if not op.isdir(folder):
            raise IOError("IFC export folder not found: {}".format(folder))

        mlogger.debug("Exporting to: {}".format(op.join(folder, filename)))

        result = self.doc.Export(folder, filename, export_options)

        mlogger.debug("Export {}".format("succeeded." if result else "FAILED."))

        return result
