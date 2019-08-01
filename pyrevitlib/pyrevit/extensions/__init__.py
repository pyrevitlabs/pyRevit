"""Base module for handling extensions parsing."""
from pyrevit import HOST_APP, EXEC_PARAMS

# Extension types
# ------------------------------------------------------------------------------
LIB_EXTENSION_POSTFIX = '.lib'
UI_EXTENSION_POSTFIX = '.extension'


class UIExtensionType:
    ID = 'extension'
    POSTFIX = '.extension'


class LIBExtensionType:
    ID = 'lib'
    POSTFIX = '.lib'


class RUNExtensionType:
    ID = 'run'
    POSTFIX = '.run'


class ExtensionTypes:
    UI_EXTENSION = UIExtensionType
    LIB_EXTENSION = LIBExtensionType
    RUN_EXTENSION = RUNExtensionType

    @classmethod
    def get_ext_types(cls):
        ext_types = set()
        for attr in dir(cls):
            if attr.endswith('_EXTENSION'):
                ext_types.add(getattr(cls, attr))
        return ext_types

    @classmethod
    def is_cli_ext(cls, ext_type):
        """Check if this is a pyRevit CLI extension."""
        return ext_type == cls.RUN_EXTENSION


# -----------------------------------------------------------------------------
# supported scripting languages
PYTHON_LANG = 'python'
CSHARP_LANG = 'csharp'
VB_LANG = 'visualbasic'
RUBY_LANG = 'ruby'
DYNAMO_LANG = 'dynamobim'
GRASSHOPPER_LANG = 'grasshopper'

# supported script files
PYTHON_SCRIPT_FILE_FORMAT = '.py'
CSHARP_SCRIPT_FILE_FORMAT = '.cs'
VB_SCRIPT_FILE_FORMAT = '.vb'
RUBY_SCRIPT_FILE_FORMAT = '.rb'
DYNAMO_SCRIPT_FILE_FORMAT = '.dyn'
GRASSHOPPER_SCRIPT_FILE_FORMAT = '.gh'

# extension startup script
EXT_STARTUP_NAME = 'startup'
EXT_STARTUP_FILE = EXT_STARTUP_NAME + PYTHON_SCRIPT_FILE_FORMAT

# -----------------------------------------------------------------------------
# supported metadata formats
YAML_FILE_FORMAT = '.yaml'
JSON_FILE_FORMAT = '.json'

# metadata filenames
EXT_MANIFEST_NAME = 'extension'
EXT_MANIFEST_FILE = EXT_MANIFEST_NAME + JSON_FILE_FORMAT

DEFAULT_BUNDLEMATA_NAME = 'script'
BUNDLEMATA_POSTFIX = DEFAULT_BUNDLEMATA_NAME + YAML_FILE_FORMAT

# metadata schema: Exensions
EXT_MANIFEST_TEMPLATES_KEY = 'templates'

# metadata schema: Bundles
MDATA_ICON_FILE = 'icon'
MDATA_UI_TITLE = 'title'
MDATA_TOOLTIP = 'tooltip'
MDATA_AUTHOR = 'author'
MDATA_AUTHORS = 'authors'
MDATA_COMMAND_HELP_URL = 'help_url'
MDATA_COMMAND_CONTEXT = 'context'
MDATA_MIN_REVIT_VERSION = 'min_revit_version'
MDATA_MAX_REVIT_VERSION = 'max_revit_version'
MDATA_BETA_SCRIPT = 'is_beta'
MDATA_ENGINE = 'engine'
MDATA_ENGINE_CLEAN = 'clean'
MDATA_ENGINE_FULLFRAME = 'full_frame'
MDATA_LINK_BUTTON_MODULES = 'modules'
MDATA_LINK_BUTTON_ASSEMBLY = 'assembly'
MDATA_LINK_BUTTON_COMMAND_CLASS = 'command_class'

# metadata schema: Bundles | legacy
UI_TITLE_PARAM = '__title__'
DOCSTRING_PARAM = '__doc__'
AUTHOR_PARAM = '__author__'
AUTHORS_PARAM = '__authors__'
COMMAND_HELP_URL_PARAM = '__helpurl__'
COMMAND_CONTEXT_PARAM = '__context__'
MIN_REVIT_VERSION_PARAM = '__min_revit_ver__'
MAX_REVIT_VERSION_PARAM = '__max_revit_ver__'
SHIFT_CLICK_PARAM = '__shiftclick__'
BETA_SCRIPT_PARAM = '__beta__'
CLEAN_ENGINE_SCRIPT_PARAM = '__cleanengine__'
FULLFRAME_ENGINE_PARAM = '__fullframeengine__'
LINK_BUTTON_ASSEMBLY = '__assembly__'
LINK_BUTTON_COMMAND_CLASS = '__commandclass__'

# -----------------------------------------------------------------------------
# supported bundles
TAB_POSTFIX = '.tab'
PANEL_POSTFIX = '.panel'
LINK_BUTTON_POSTFIX = '.linkbutton'
INVOKE_BUTTON_POSTFIX = '.invokebutton'
PUSH_BUTTON_POSTFIX = '.pushbutton'
TOGGLE_BUTTON_POSTFIX = '.toggle'
SMART_BUTTON_POSTFIX = '.smartbutton'
PULLDOWN_BUTTON_POSTFIX = '.pulldown'
STACKTHREE_BUTTON_POSTFIX = '.stack3'
STACKTWO_BUTTON_POSTFIX = '.stack2'
SPLIT_BUTTON_POSTFIX = '.splitbutton'
SPLITPUSH_BUTTON_POSTFIX = '.splitpushbutton'
PANEL_PUSH_BUTTON_POSTFIX = '.panelbutton'
NOGUI_COMMAND_POSTFIX = '.nobutton'

# known bundle sub-directories
COMP_LIBRARY_DIR_NAME = 'lib'
COMP_BIN_DIR_NAME = 'bin'

# unique ids
UNIQUE_ID_SEPARATOR = '-'

# bundle layout elements
DEFAULT_LAYOUT_FILE_NAME = '_layout'
SEPARATOR_IDENTIFIER = '---'
SLIDEOUT_IDENTIFIER = '>>>'

# bundle icon
ICON_FILE_FORMAT = '.png'
DEFAULT_ICON_FILE = 'icon' + ICON_FILE_FORMAT
DEFAULT_ON_ICON_FILE = 'on' + ICON_FILE_FORMAT
DEFAULT_OFF_ICON_FILE = 'off' + ICON_FILE_FORMAT

# bundle image for tooltips
DEFAULT_TOOLTIP_IMAGE_FILE = 'tooltip.png'
# bundle video for tooltips
DEFAULT_TOOLTIP_VIDEO_FILE = 'tooltip.swf'
if not EXEC_PARAMS.doc_mode and HOST_APP.is_newer_than(2019, or_equal=True):
    DEFAULT_TOOLTIP_VIDEO_FILE = 'tooltip.mp4'

# bundle scripts
DEFAULT_SCRIPT_NAME = 'script'
DEFAULT_CONFIG_NAME = 'config'

# script files
PYTHON_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + PYTHON_SCRIPT_FILE_FORMAT
CSHARP_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + CSHARP_SCRIPT_FILE_FORMAT
VB_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + VB_SCRIPT_FILE_FORMAT
RUBY_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + RUBY_SCRIPT_FILE_FORMAT
DYNAMO_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + DYNAMO_SCRIPT_FILE_FORMAT
GRASSHOPPER_SCRIPT_POSTFIX = \
    DEFAULT_SCRIPT_NAME + GRASSHOPPER_SCRIPT_FILE_FORMAT
CONFIG_SCRIPT_POSTFIX = DEFAULT_CONFIG_NAME + PYTHON_SCRIPT_FILE_FORMAT

# Hash file for caching directory state hash value
EXTENSION_HASH_CACHE_FILENAME = 'ext_hash'

# -----------------------------------------------------------------------------
# Command bundle defaults
COMMAND_AVAILABILITY_NAME_POSTFIX = 'Availab'
CTX_SELETION = 'selection'
CTX_ZERODOC = ['zero-doc', 'zerodoc']
