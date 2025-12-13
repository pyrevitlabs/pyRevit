# -*- coding: utf-8 -*-

from os import walk
from os.path import join, isdir, isfile, basename
import traceback
import collections
import fnmatch

from pyrevit import HOST_APP, forms, script, revit, EXEC_PARAMS
from pyrevit import DB

doc = HOST_APP.doc
logger = script.get_logger()
output = script.get_output()

# Get script configuration
config = script.get_config()


class ConfigurationManager:
    """Manages texture folder configuration and persistence."""
    
    def __init__(self, config):
        """Initialize ConfigurationManager with pyRevit config object."""
        self.config = config
    
    def load_folders(self):
        """Load saved folder paths from config."""
        folders = self.config.get_option("texture_folders", [])
        return folders if isinstance(folders, list) else []
    
    def save_folders(self, folders):
        """Save folder paths to config."""
        try:
            self.config.texture_folders = folders
            script.save_config()
            return True
        except (OSError, IOError, ValueError) as error:
            logger.error("Failed to save config: {}".format(error))
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
    
    def __init__(self):
        """Initialize TextureIndexer."""
        self.index = collections.defaultdict(list)
    
    def get_all_roots(self, config_manager):
        """Get all root folders from configuration only."""
        roots = config_manager.load_folders()
        return roots
    
    def unique_existing_paths(self, paths):
        """Return unique, existing directory paths."""
        seen = set()
        result = []
        for path in paths:
            if path and path not in seen and isdir(path):
                seen.add(path)
                result.append(path)
        return result
    
    
    def build_index(self, roots):
        """Map filename to full paths for fast lookup."""
        self.index = collections.defaultdict(list)
        valid_roots = self.unique_existing_paths(roots)
        
        # Define common texture file extensions
        texture_extensions = ('*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tga', '*.tiff', '*.tif', '*.dds')
        
        # Directories to skip for faster traversal
        skip_dirs = {
            # Version control
            '.git', '.svn', '.hg',
            # Build/cache
            'node_modules', '__pycache__', '.pyc',
            # System files
            '.DS_Store', 'Thumbs.db', 'Desktop.ini',
            # Windows system
            '$RECYCLE.BIN', 'System Volume Information',
            # Revit specific
            'backup', 'Backup'
        }
        
        output.log_info("Indexing {} folder(s)...".format(len(valid_roots)))
        
        for i, root in enumerate(valid_roots):
            try:
                for dirpath, dirs, files in walk(root):
                    # Remove directories we want to skip (including all hidden folders)
                    dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
                    
                    # Filter files by texture extensions using fnmatch
                    texture_files = []
                    for pattern in texture_extensions:
                        texture_files.extend(fnmatch.filter(files, pattern))
                    
                    # Add texture files to index
                    for filename in texture_files:
                        self.index[filename.lower()].append(join(dirpath, filename))
                        
            except (OSError, IOError) as error:
                logger.warning("Failed to index {}: {}".format(root, error))
        
        output.log_info("Index complete. Found {} texture files.".format(len(self.index)))
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
            return hits[0]
        
        return None


class AssetProcessor:
    """Handles Revit appearance asset processing and texture relinking."""
    
    def __init__(self, doc):
        """Initialize AssetProcessor with Revit document."""
        self.doc = doc
    
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
            
            return assets
        
        except (OSError, IOError, ValueError, AttributeError) as error:
            logger.error("Failed to collect materials: {}".format(error))
            return []
    
    def relink_asset_textures(self, asset, indexer, roots, unresolved):
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
                    
                if not isinstance(connected, DB.Visual.Asset):
                    continue

                try:
                    path_prop = connected.FindByName(DB.Visual.UnifiedBitmap.UnifiedbitmapBitmap)
                except AttributeError:
                    continue
                    
                if isinstance(path_prop, DB.Visual.AssetPropertyString):
                    current_path = path_prop.Value
                    
                    if current_path and isfile(current_path):
                        continue
                    
                    name = basename(current_path) if current_path else None
                    if name:
                        hit = indexer.find_texture(name, roots)
                        if hit and (not current_path or hit.lower() != current_path.lower()):
                            try:
                                path_prop.Value = hit
                                count += 1
                            except Exception as error:
                                logger.warning("Failed to set path for {}: {}".format(name, error))
                        else:
                            unresolved.add(name)

                count += self.relink_asset_textures(connected, indexer, roots, unresolved)
        
        return count
    
    def process_single_asset(self, asset_element, indexer, roots, unresolved):
        """Process a single appearance asset element."""
        if not asset_element or not isinstance(asset_element, DB.AppearanceAssetElement):
            logger.warning("Invalid asset element provided for processing")
            return 0
        
        fixed_count = 0
        scope = None
        
        try:
            scope = DB.Visual.AppearanceAssetEditScope(self.doc)
            editable = scope.Start(asset_element.Id)
            if editable:
                fixed_count = self.relink_asset_textures(editable, indexer, roots, unresolved)
                scope.Commit(True)
            else:
                logger.warning("Failed to start edit scope for asset: {}".format(
                    getattr(asset_element, 'Name', 'Unknown')))
        except (OSError, IOError, ValueError, AttributeError) as error:
            logger.error("Asset edit failed for {}: {}".format(
                getattr(asset_element, 'Name', 'Unknown'), error))
        finally:
            if scope:
                scope.Dispose()
        
        return fixed_count


class TextureRelinker:
    """Main controller class for texture relinking operations."""
    
    def __init__(self, doc, config):
        """Initialize TextureRelinker with Revit document and config."""
        self.doc = doc
        self.config_manager = ConfigurationManager(config)
        self.indexer = TextureIndexer()
        self.processor = AssetProcessor(doc)
    
    def run_relink(self):
        """Execute the main texture relinking logic."""
        roots = self.indexer.get_all_roots(self.config_manager)
        
        if not roots:
            forms.alert(
                "No search folders configured.\n\n"
                "Please configure at least one folder to search for textures.",
                title="Configuration Needed"
            )
            return
        
        assets = self.processor.collect_appearance_assets()
        if not assets:
            forms.alert("Failed to collect materials. See output for details.", title="Error")
            return

        self.indexer.build_index(roots)

        fixed_count = 0
        examined = 0
        unresolved = set()

        output.log_info("Relinking {} appearance assets...".format(len(assets)))
        
        with revit.Transaction("Relink material textures"):
            for i, asset_element in enumerate(assets):
                examined += 1
                fixed_count += self.processor.process_single_asset(
                    asset_element, self.indexer, roots, unresolved)
                
        # Display results in output window
        output.log_info("Relink complete. {} textures relinked.".format(fixed_count))
        
        if unresolved:
            logger.warning("Unresolved textures: {} (see list below)".format(len(unresolved)))
            logger.warning("UNRESOLVED TEXTURE NAMES:")
            for name in sorted(unresolved):
                logger.warning("  • {}".format(name))
    
    def show_main_menu(self):
        """Show unified main menu dialog with folder management and relink options."""
        while True:
            current_folders = self.config_manager.load_folders()
            
            # Build folder list display
            if current_folders:
                folder_list = "\n".join("  • {}".format(folder) for folder in current_folders)
                message = "The whole process will take a while depending on the number of textures and folders.\n\nCurrent search folders:\n\n{}\n\nWhat would you like to do?".format(folder_list)
                options = ["Add Folder", "Remove Folder", "Clear All", "Relink Textures Now", "Cancel"]
            else:
                message = "No search folders configured yet.\n\nWhat would you like to do?"
                options = ["Add Folder", "Cancel"]
            
            choice = forms.alert(
                message,
                title="Texture Relink Tool",
                options=options
            )
            
            if choice == "Add Folder":
                folder = forms.pick_folder()
                if folder and folder not in current_folders:
                    current_folders.append(folder)
                    self.config_manager.save_folders(current_folders)
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
                        self.config_manager.save_folders(current_folders)
            
            elif choice == "Clear All":
                if current_folders:
                    self.config_manager.save_folders([])
                else:
                    forms.alert("No folders to clear.", title="Clear All")
            
            elif choice == "Relink Textures Now":
                self.run_relink()
                break
            
            else:  # Cancel or None (X button)
                break


if __name__ == '__main__':
    try:
        relinker = TextureRelinker(doc, config)
        relinker.show_main_menu()
    
    except Exception as error:
        logger.error("Script error: {}".format(error))
        logger.error(traceback.format_exc())
        forms.alert(
            "Script error occurred:\n\n{}".format(str(error)),
            title="Error"
        )