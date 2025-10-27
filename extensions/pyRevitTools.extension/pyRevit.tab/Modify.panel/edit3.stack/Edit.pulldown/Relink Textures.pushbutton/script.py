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

# Constants
TRANSACTION_NAME = "Relink material textures"
LOG_SEPARATOR_LENGTH = 60
LOG_SEPARATOR_CHAR = "="
CONFIG_KEY_TEXTURE_FOLDERS = 'texture_folders'


class ConfigurationManager:
    """Manages texture folder configuration and persistence."""
    
    def __init__(self, config):
        self.config = config
        self.logger = script.get_logger()
    
    def load_folders(self):
        """Load saved folder paths from config."""
        folders = self.config.get_option(CONFIG_KEY_TEXTURE_FOLDERS, [])
        return folders if isinstance(folders, list) else []
    
    def save_folders(self, folders):
        """Save folder paths to config."""
        try:
            self.config.texture_folders = folders
            script.save_config()
            return True
        except Exception as error:
            self.logger.error("Failed to save config: {}".format(error))
            return False
    
    def show_configuration_dialog(self):
        """Launch the configuration dialog using native pyRevit forms."""
        current_folders = self.load_folders()
        
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
                    self.logger.info("Added folder: {}".format(folder))
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
                        self.logger.info("Removed folder: {}".format(folder_to_remove))
            
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
                        self.logger.info("Cleared all folders")
                else:
                    forms.alert("No folders to clear.", title="Clear All")
            
            else:  # Done or None (X button clicked)
                if self.save_folders(current_folders):
                    forms.alert(
                        "Configuration saved!\n\n{} folder(s) configured.".format(len(current_folders)),
                        title="Configuration Saved"
                    )
                break


class TextureIndexer:
    """Handles texture indexing and path resolution."""
    
    def __init__(self, logger):
        self.logger = logger
        self.index = collections.defaultdict(list)
    
    def get_project_directory(self, doc):
        """Get project directory if available."""
        if doc.PathName:
            proj_dir = dirname(doc.PathName)
            if proj_dir and isdir(proj_dir):
                return proj_dir
        return None
    
    def get_all_roots(self, doc):
        """Get all root folders including project directory."""
        roots = self.config_manager.load_folders() if hasattr(self, 'config_manager') else []
        
        proj_dir = self.get_project_directory(doc)
        if proj_dir and proj_dir not in roots:
            roots.append(proj_dir)
        
        return roots
    
    def unique_existing_paths(self, paths):
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
    
    def build_index(self, roots):
        """Map filename to full paths for fast lookup."""
        self.index = collections.defaultdict(list)
        valid_roots = self.unique_existing_paths(roots)
        
        self.logger.info("Building texture index from {} folder(s)...".format(len(valid_roots)))
        
        for root in valid_roots:
            self.logger.info("  Indexing: {}".format(root))
            try:
                for dirpath, _, files in walk(root):
                    for filename in files:
                        self.index[filename.lower()].append(join(dirpath, filename))
            except (OSError, IOError) as error:
                self.logger.warning("Failed to index {}: {}".format(root, error))
        
        self.logger.info("Indexed {} unique texture names".format(len(self.index)))
        return self.index
    
    def find_texture(self, name, roots):
        """Try quick direct hits first, then index lookup."""
        if not name:
            return None
        
        for root in self.unique_existing_paths(roots):
            direct = join(root, name)
            if isfile(direct):
                return direct
        
        hits = self.index.get(name.lower())
        if hits:
            hits.sort()
            return hits[0]
        
        return None


class AssetProcessor:
    """Handles Revit appearance asset processing and texture relinking."""
    
    def __init__(self, doc, logger):
        self.doc = doc
        self.logger = logger
    
    def collect_appearance_assets(self):
        """Collect all appearance assets from materials in the document."""
        try:
            materials = DB.FilteredElementCollector(self.doc).OfClass(DB.Material).ToElements()
            asset_ids = set()
            
            for material in materials:
                if hasattr(material, "AppearanceAssetId"):
                    asset_id = material.AppearanceAssetId
                    if asset_id and asset_id != DB.ElementId.InvalidElementId:
                        asset_ids.add(asset_id)
            
            assets = []
            for asset_id in asset_ids:
                element = self.doc.GetElement(asset_id)
                if element:
                    assets.append(element)
            
            self.logger.info("Found {} appearance assets to check".format(len(assets)))
            return assets
        
        except Exception as error:
            self.logger.error("Failed to collect materials: {}".format(error))
            self.logger.error(traceback.format_exc())
            return []
    
    def relink_asset_textures(self, asset, indexer, unresolved):
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
                        hit = indexer.find_texture(name, indexer.get_all_roots(self.doc))
                        if hit and (not current_path or hit.lower() != current_path.lower()):
                            try:
                                path_prop.Value = hit
                                count += 1
                                self.logger.debug("Relinked: {} -> {}".format(name, hit))
                            except Exception as error:
                                self.logger.warning("Failed to set path for {}: {}".format(name, error))
                        else:
                            unresolved.add(name)

                try:
                    count += self.relink_asset_textures(connected, indexer, unresolved)
                except Exception:
                    pass
        
        return count
    
    def process_single_asset(self, asset_element, indexer, unresolved):
        """Process a single appearance asset element."""
        if not isinstance(asset_element, DB.AppearanceAssetElement):
            return 0
        
        fixed_count = 0
        scope = None
        
        try:
            scope = AppearanceAssetEditScope(self.doc)
            editable = scope.Start(asset_element.Id)
            fixed_count = self.relink_asset_textures(editable, indexer, unresolved)
            scope.Commit(True)
        except Exception as error:
            self.logger.error("Asset edit failed for {}: {}".format(
                getattr(asset_element, 'Name', 'Unknown'), error))
        finally:
            if scope:
                try:
                    scope.Dispose()
                except Exception:
                    pass
        
        return fixed_count


class TextureRelinker:
    """Main controller class for texture relinking operations."""
    
    def __init__(self, doc, config):
        self.doc = doc
        self.config_manager = ConfigurationManager(config)
        self.indexer = TextureIndexer(logger)
        self.processor = AssetProcessor(doc, logger)
        self.logger = logger
    
    def run_relink(self):
        """Execute the main texture relinking logic."""
        roots = self.indexer.get_all_roots(self.doc)
        
        if not roots:
            forms.alert(
                "No search folders configured.\n\n"
                "Please configure at least one folder to search for textures.",
                title="Configuration Needed"
            )
            return
        
        self.logger.info(LOG_SEPARATOR_CHAR * LOG_SEPARATOR_LENGTH)
        self.logger.info("Starting texture relink process...")
        self.logger.info("Search folders: {}".format(roots))
        
        assets = self.processor.collect_appearance_assets()
        if not assets:
            forms.alert("Failed to collect materials. See output for details.", title="Error")
            return

        self.indexer.build_index(roots)

        fixed_count = 0
        examined = 0
        unresolved = set()

        with revit.Transaction(TRANSACTION_NAME):
            for asset_element in assets:
                examined += 1
                fixed_count += self.processor.process_single_asset(
                    asset_element, self.indexer, unresolved)
        
        self.logger.info("Transaction committed successfully")

        # Show results
        msg = "Appearance assets examined: {}\nTextures relinked: {}".format(examined, fixed_count)
        
        if unresolved:
            msg += "\n\nUnresolved textures: {} (see output panel for list)".format(len(unresolved))
            self.logger.warning(LOG_SEPARATOR_CHAR * LOG_SEPARATOR_LENGTH)
            self.logger.warning("UNRESOLVED TEXTURE NAMES:")
            self.logger.warning(LOG_SEPARATOR_CHAR * LOG_SEPARATOR_LENGTH)
            for name in sorted(unresolved):
                self.logger.warning("  • {}".format(name))
            self.logger.warning(LOG_SEPARATOR_CHAR * LOG_SEPARATOR_LENGTH)
        
        self.logger.info(LOG_SEPARATOR_CHAR * LOG_SEPARATOR_LENGTH)
        forms.alert(msg, title="Relink Complete")
    
    def run_configuration(self):
        """Run configuration mode."""
        self.config_manager.show_configuration_dialog()
    
    def show_main_menu(self):
        """Show main menu dialog."""
        choice = forms.alert(
            "Texture Relink Tool\n\nWhat would you like to do?",
            title="Relink Material Textures",
            options=["Relink Textures Now", "Configure Search Folders", "Cancel"]
        )
        
        if choice == "Relink Textures Now":
            self.run_relink()
        elif choice == "Configure Search Folders":
            self.run_configuration()


# Main execution
if __name__ == '__main__':
    try:
        relinker = TextureRelinker(doc, config)
        
        if EXEC_PARAMS.config_mode:
            relinker.run_configuration()
        else:
            relinker.show_main_menu()
    
    except Exception as error:
        logger.error("Script error: {}".format(error))
        logger.error(traceback.format_exc())
        forms.alert(
            "Script error occurred:\n\n{}".format(str(error)),
            title="Error"
        )