# -*- coding: utf-8 -*-

from os import walk
from os.path import dirname, join, isdir, isfile, basename
import traceback
import collections

from pyrevit import HOST_APP, forms, script, revit, EXEC_PARAMS
from pyrevit import DB

from Autodesk.Revit.DB.Visual import (
    AppearanceAssetEditScope, 
    UnifiedBitmap, 
    Asset, 
    AssetPropertyString
)

doc = HOST_APP.doc
logger = script.get_logger()
output = script.get_output()

# Get script configuration
config = script.get_config()


def load_roots():
    """Load saved folder paths from config."""
    folders = config.get_option('texture_folders', [])
    return folders if isinstance(folders, list) else []


def save_roots(folders):
    """Save folder paths to config."""
    try:
        config.texture_folders = folders
        script.save_config()
        return True
    except Exception as error:
        logger.error("Failed to save config: {}".format(error))
        return False


def run_config():
    """Launch the configuration dialog using native pyRevit forms."""
    current_folders = load_roots()
    
    while True:
        if current_folders:
            folder_list = "\n".join("  • {}".format(folder) for folder in current_folders)
            message = "Current search folders:\n\n{}\n\nWhat would you like to do?".format(folder_list)
        else:
            message = "No search folders configured yet.\n\nWhat would you like to do?"
        
        choice = forms.alert(
            message,
            title="Manage Texture Search Folders",
            options=["Add Folder", "Remove Folder", "Clear All", "Done"]
        )
        
        if choice == "Add Folder":
            folder = forms.pick_folder()
            if folder and folder not in current_folders:
                current_folders.append(folder)
                logger.info("Added folder: {}".format(folder))
            elif folder in current_folders:
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
    
    if doc.PathName:
        proj_dir = dirname(doc.PathName)
        if proj_dir and isdir(proj_dir) and proj_dir not in roots:
            roots.append(proj_dir)
    
    return roots


def unique_existing_paths(paths):
    """Return unique, existing directory paths."""
    seen = set()
    result = []
    for path in paths:
        if not path or path in seen:
            continue
        seen.add(path)
        if isdir(path):
            result.append(path)
    return result


def build_name_index(roots):
    """Map filename to full paths for fast lookup."""
    index = collections.defaultdict(list)
    valid_roots = unique_existing_paths(roots)
    
    logger.info("Building texture index from {} folder(s)...".format(len(valid_roots)))
    
    for root in valid_roots:
        logger.info("  Indexing: {}".format(root))
        try:
            for dirpath, _, files in walk(root):
                for filename in files:
                    index[filename.lower()].append(join(dirpath, filename))
        except (OSError, IOError) as error:
            logger.warning("Failed to index {}: {}".format(root, error))
    
    logger.info("Indexed {} unique texture names".format(len(index)))
    return index


def resolve_by_name(name, roots, index):
    """Try quick direct hits first, then index lookup."""
    if not name:
        return None
    
    for root in unique_existing_paths(roots):
        direct = join(root, name)
        if isfile(direct):
            return direct
    
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
    except AttributeError:
        return 0

    for idx in range(size):
        try:
            asset_prop = asset[idx]
        except IndexError:
            continue
        
        try:
            conn_count = asset_prop.NumberOfConnectedProperties
        except AttributeError:
            continue

        for conn_idx in range(conn_count):
            try:
                connected = asset_prop.GetConnectedProperty(conn_idx)
            except (IndexError, AttributeError):
                continue
                
            if not isinstance(connected, Asset):
                continue

            try:
                path_prop = connected.FindByName(UnifiedBitmap.UnifiedbitmapBitmap)
            except AttributeError:
                continue
                
            if isinstance(path_prop, AssetPropertyString):
                current_path = path_prop.Value
                
                if current_path and isfile(current_path):
                    continue
                
                name = basename(current_path) if current_path else None
                if name:
                    hit = resolve_by_name(name, roots, index)
                    if hit and (not current_path or hit.lower() != current_path.lower()):
                        try:
                            path_prop.Value = hit
                            count += 1
                            logger.debug("Relinked: {} -> {}".format(name, hit))
                        except Exception as error:
                            logger.warning("Failed to set path for {}: {}".format(name, error))
                    else:
                        unresolved.add(name)

            try:
                count += relink_asset(connected, roots, index, unresolved)
            except Exception:
                pass
    
    return count


def collect_appearance_assets():
    """Collect all appearance assets from materials in the document."""
    try:
        materials = DB.FilteredElementCollector(doc).OfClass(DB.Material).ToElements()
        asset_ids = set()
        
        for material in materials:
            if hasattr(material, "AppearanceAssetId"):
                asset_id = material.AppearanceAssetId
                if asset_id and asset_id != DB.ElementId.InvalidElementId:
                    asset_ids.add(asset_id)
        
        assets = []
        for asset_id in asset_ids:
            element = doc.GetElement(asset_id)
            if element:
                assets.append(element)
        
        logger.info("Found {} appearance assets to check".format(len(assets)))
        return assets
    
    except Exception as error:
        logger.error("Failed to collect materials: {}".format(error))
        logger.error(traceback.format_exc())
        return []


def process_single_asset(asset_element, roots, name_index, unresolved):
    """Process a single appearance asset element."""
    if not isinstance(asset_element, DB.AppearanceAssetElement):
        return 0
    
    fixed_count = 0
    scope = None
    
    try:
        scope = AppearanceAssetEditScope(doc)
        editable = scope.Start(asset_element.Id)
        fixed_count = relink_asset(editable, roots, name_index, unresolved)
        scope.Commit(True)
    except Exception as error:
        logger.error("Asset edit failed for {}: {}".format(
            getattr(asset_element, 'Name', 'Unknown'), error))
    finally:
        if scope:
            try:
                scope.Dispose()
            except Exception:
                pass
    
    return fixed_count


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
    
    assets = collect_appearance_assets()
    if not assets:
        forms.alert("Failed to collect materials. See output for details.", title="Error")
        return

    name_index = build_name_index(roots)

    fixed_count = 0
    examined = 0
    unresolved = set()

    with revit.Transaction("Relink material textures"):
        for asset_element in assets:
            examined += 1
            fixed_count += process_single_asset(asset_element, roots, name_index, unresolved)
    
    logger.info("Transaction committed successfully")

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


# Main execution
if __name__ == '__main__':
    try:
        if EXEC_PARAMS.config_mode:
            run_config()
        else:
            choice = forms.alert(
                "Texture Relink Tool\n\nWhat would you like to do?",
                title="Relink Material Textures",
                options=["Relink Textures Now", "Configure Search Folders", "Cancel"]
            )
            
            if choice == "Relink Textures Now":
                run_relink()
            elif choice == "Configure Search Folders":
                run_config()
    
    except Exception as error:
        logger.error("Script error: {}".format(error))
        logger.error(traceback.format_exc())
        forms.alert(
            "Script error occurred:\n\n{}".format(str(error)),
            title="Error"
        )