# -*- coding: utf-8 -*-
"""Relink material textures for Revit via pyRevit."""

__title__ = "Relink\nTextures"
__author__ = "SwichTools"

# Standard library imports
import os
import json
import traceback
import collections

# pyRevit imports
from pyrevit import forms, script

# Revit API imports
from Autodesk.Revit.DB import (
    FilteredElementCollector, 
    Material, 
    AppearanceAssetElement,
    ElementId, 
    Transaction
)
from Autodesk.Revit.DB.Visual import (
    AppearanceAssetEditScope, 
    UnifiedBitmap, 
    Asset, 
    AssetPropertyString
)

# Document and logger
doc = __revit__.ActiveUIDocument.Document
logger = script.get_logger()
output = script.get_output()

# Configuration file path
CONFIG_FILE = os.path.join(
    os.getenv('APPDATA'),
    'pyRevit_TextureRelink_Config.json'
)


def load_roots():
    """Load saved folder paths from config file."""
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                return data.get('folders', [])
        except Exception as e:
            logger.warning("Failed to load config: {}".format(e))
    return []


def save_roots(folders):
    """Save folder paths to config file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'folders': folders}, f, indent=2)
        return True
    except Exception as e:
        logger.error("Failed to save config: {}".format(e))
        return False


def run_config():
    """Launch the configuration dialog using native pyRevit forms."""
    current_folders = load_roots()
    
    while True:
        # Build display of current folders
        if current_folders:
            folder_list = "\n".join("  • {}".format(f) for f in current_folders)
            message = "Current search folders:\n\n{}\n\nWhat would you like to do?".format(folder_list)
        else:
            message = "No search folders configured yet.\n\nWhat would you like to do?"
        
        # Show options
        choice = forms.alert(
            message,
            title="Manage Texture Search Folders",
            options=["Add Folder", "Remove Folder", "Clear All", "Done"]
        )
        
        if choice == "Add Folder":
            folder = forms.pick_folder()
            if folder:
                if folder not in current_folders:
                    current_folders.append(folder)
                    logger.info("Added folder: {}".format(folder))
                else:
                    forms.alert("This folder is already in the list.", title="Duplicate Folder")
        
        elif choice == "Remove Folder":
            if not current_folders:
                forms.alert("No folders to remove.", title="Remove Folder")
            else:
                folder_to_remove = forms.SelectFromList.show(
                    current_folders,
                    title="Select Folder to Remove",
                    button_name="Remove",
                    multiselect=False
                )
                if folder_to_remove:
                    current_folders.remove(folder_to_remove)
                    logger.info("Removed folder: {}".format(folder_to_remove))
        
        elif choice == "Clear All":
            if current_folders:
                confirm = forms.alert(
                    "Are you sure you want to remove all {} folder(s)?".format(len(current_folders)),
                    title="Clear All Folders",
                    yes=True,
                    no=True
                )
                if confirm:
                    current_folders = []
                    logger.info("Cleared all folders")
            else:
                forms.alert("No folders to clear.", title="Clear All")
        
        else:  # Done or None (X button clicked)
            if save_roots(current_folders):
                forms.alert(
                    "Configuration saved!\n\n{} folder(s) configured.".format(len(current_folders)),
                    title="Configuration Saved"
                )
            break


def get_roots():
    """Get all root folders including project directory."""
    roots = load_roots()
    
    # Auto-add project directory if document is saved
    if doc.PathName:
        proj_dir = os.path.dirname(doc.PathName)
        if proj_dir and os.path.isdir(proj_dir):
            if proj_dir not in roots:
                roots.append(proj_dir)
    
    return roots


def unique_existing_paths(paths):
    """Return unique, existing directory paths."""
    seen = set()
    out = []
    for p in paths:
        if not p or p in seen:
            continue
        seen.add(p)
        if os.path.isdir(p):
            out.append(p)
    return out


def build_name_index(roots):
    """Map filename to full paths for fast lookup."""
    index = collections.defaultdict(list)
    valid_roots = unique_existing_paths(roots)
    
    logger.info("Building texture index from {} folder(s)...".format(len(valid_roots)))
    
    for root in valid_roots:
        logger.info("  Indexing: {}".format(root))
        try:
            for r, _, files in os.walk(root):
                for f in files:
                    index[f.lower()].append(os.path.join(r, f))
        except Exception as e:
            logger.warning("Failed to index {}: {}".format(root, e))
    
    logger.info("Indexed {} unique texture names".format(len(index)))
    return index


def resolve_by_name(name, roots, index):
    """Try quick direct hits first, then index lookup."""
    if not name:
        return None
    
    # Try direct path in each root first
    for root in unique_existing_paths(roots):
        direct = os.path.join(root, name)
        if os.path.isfile(direct):
            return direct
    
    # Fall back to index lookup
    hits = index.get(name.lower())
    if hits:
        hits.sort()
        return hits[0]
    
    return None


def relink_asset(asset, roots, index, unresolved):
    """Walk connected assets and relink UnifiedBitmap Source paths."""
    count = 0
    
    try:
        size = asset.Size
    except:
        return 0

    for i in range(size):
        try:
            ap = asset[i]
        except:
            continue
        
        try:
            con_count = ap.NumberOfConnectedProperties
        except:
            continue

        for c in range(con_count):
            try:
                connected = ap.GetConnectedProperty(c)
            except:
                continue
                
            if not isinstance(connected, Asset):
                continue

            # Look for bitmap path property
            try:
                path_prop = connected.FindByName(UnifiedBitmap.UnifiedbitmapBitmap)
            except:
                continue
                
            if isinstance(path_prop, AssetPropertyString):
                cur = path_prop.Value
                
                # Check if current path exists
                if cur and os.path.isfile(cur):
                    pass  # Path is valid, skip
                else:
                    # Try to resolve the texture
                    name = os.path.basename(cur) if cur else None
                    if name:
                        hit = resolve_by_name(name, roots, index)
                        if hit and (not cur or hit.lower() != cur.lower()):
                            try:
                                path_prop.Value = hit
                                count += 1
                                logger.debug("Relinked: {} -> {}".format(name, hit))
                            except Exception as e:
                                logger.warning("Failed to set path for {}: {}".format(name, e))
                        else:
                            unresolved.add(name)

            # Recursively check nested assets
            try:
                count += relink_asset(connected, roots, index, unresolved)
            except:
                pass
    
    return count


def run_relink():
    """Execute the main texture relinking logic."""
    roots = get_roots()
    
    if not roots:
        forms.alert(
            "No search folders configured.\n\n"
            "Please configure at least one folder to search for textures.",
            title="Configuration Needed"
        )
        return
    
    logger.info("=" * 60)
    logger.info("Starting texture relink process...")
    logger.info("Search folders: {}".format(roots))
    
    # Collect all materials with appearance assets
    try:
        mats = FilteredElementCollector(doc).OfClass(Material).ToElements()
        asset_ids = set()
        
        for m in mats:
            if hasattr(m, "AppearanceAssetId"):
                aid = m.AppearanceAssetId
                if aid and aid != ElementId.InvalidElementId:
                    asset_ids.add(aid)
        
        assets = []
        for aid in asset_ids:
            elem = doc.GetElement(aid)
            if elem:
                assets.append(elem)
        
        logger.info("Found {} appearance assets to check".format(len(assets)))
    except Exception as e:
        logger.error("Failed to collect materials: {}".format(e))
        forms.alert("Failed to collect materials. See output for details.", title="Error")
        return

    # Build texture index
    name_index = build_name_index(roots)

    fixed_count = 0
    examined = 0
    unresolved = set()

    # Start transaction
    t = Transaction(doc, "Relink material textures")
    
    try:
        t.Start()
        
        for a_elem in assets:
            if not isinstance(a_elem, AppearanceAssetElement):
                continue
            
            examined += 1
            scope = None
            
            try:
                scope = AppearanceAssetEditScope(doc)
                editable = scope.Start(a_elem.Id)
                fixed_count += relink_asset(editable, roots, name_index, unresolved)
                scope.Commit(True)
            except Exception as ex:
                logger.error("Asset edit failed for {}: {}".format(a_elem.Name, ex))
            finally:
                if scope:
                    try:
                        scope.Dispose()
                    except:
                        pass
        
        t.Commit()
        logger.info("Transaction committed successfully")
        
    except Exception as e:
        logger.error("Relink transaction failed: {}".format(e))
        logger.error(traceback.format_exc())
        
        try:
            t.RollBack()
        except:
            pass
        
        forms.alert(
            "Relink failed. See output panel for details.",
            title="Relink Textures"
        )
        return

    # Show results
    msg = "Appearance assets examined: {}\nTextures relinked: {}".format(examined, fixed_count)
    
    if unresolved:
        msg += "\n\nUnresolved textures: {} (see output panel for list)".format(len(unresolved))
        logger.warning("=" * 60)
        logger.warning("UNRESOLVED TEXTURE NAMES:")
        logger.warning("=" * 60)
        for name in sorted(unresolved):
            logger.warning("  • {}".format(name))
        logger.warning("=" * 60)
    
    logger.info("=" * 60)
    forms.alert(msg, title="Relink Complete")


# Main execution - pyRevit will run this automatically
try:
    # Check if SHIFT is pressed for quick-config
    shift_click = False
    try:
        shift_click = __shiftclick__
    except:
        pass
    
    if shift_click:
        run_config()
    else:
        # Show main menu
        choice = forms.alert(
            "Texture Relink Tool\n\nWhat would you like to do?",
            title="Relink Material Textures",
            options=["Relink Textures Now", "Configure Search Folders", "Cancel"]
        )
        
        if choice == "Relink Textures Now":
            run_relink()
        elif choice == "Configure Search Folders":
            run_config()

except Exception as e:
    # Catch-all error handler
    logger.error("Script error: {}".format(e))
    logger.error(traceback.format_exc())
    forms.alert(
        "Script error occurred:\n\n{}".format(str(e)),
        title="Error"
    )