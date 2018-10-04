"""Base module for handling extensions parsing."""
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


class ExtensionTypes:
    UI_EXTENSION = UIExtensionType
    LIB_EXTENSION = LIBExtensionType


# UI_EXTENSION_POSTFIX components
# ------------------------------------------------------------------------------
PYTHON_SCRIPT_FILE_FORMAT = '.py'
CSHARP_SCRIPT_FILE_FORMAT = '.cs'
VB_SCRIPT_FILE_FORMAT = '.vb'
RUBY_SCRIPT_FILE_FORMAT = '.rb'
DYNAMO_SCRIPT_FILE_FORMAT = '.dyn'
YAML_FILE_FORMAT = '.yaml'
JSON_FILE_FORMAT = '.json'

EXT_MANIFEST_NAME = 'extension'
EXT_MANIFEST_TEMPLATES_KEY = 'templates'
EXT_MANIFEST_FILE = EXT_MANIFEST_NAME + JSON_FILE_FORMAT

EXT_STARTUP_NAME = 'startup'
EXT_STARTUP_FILE = EXT_STARTUP_NAME + PYTHON_SCRIPT_FILE_FORMAT

TAB_POSTFIX = '.tab'
PANEL_POSTFIX = '.panel'
LINK_BUTTON_POSTFIX = '.linkbutton'
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

# Component layout elements
DEFAULT_LAYOUT_FILE_NAME = '_layout'
SEPARATOR_IDENTIFIER = '---'
SLIDEOUT_IDENTIFIER = '>>>'

# Component icon
ICON_FILE_FORMAT = '.png'

DEFAULT_ICON_FILE = 'icon' + ICON_FILE_FORMAT
DEFAULT_ON_ICON_FILE = 'on' + ICON_FILE_FORMAT
DEFAULT_OFF_ICON_FILE = 'off' + ICON_FILE_FORMAT

# Component swf video for tooltips
DEFAULT_TOOLTIP_VIDEO_FILE = 'tooltip.swf'

# Command supported languages
PYTHON_LANG = 'python'
CSHARP_LANG = 'csharp'
VB_LANG = 'visualbasic'
DYNAMO_LANG = 'dynamobim'

# Component scripts
DEFAULT_SCRIPT_NAME = 'script'
DEFAULT_CONFIG_NAME = 'config'

# Hash file for caching directory state hash value
EXTENSION_HASH_CACHE_FILENAME = 'ext_hash'

# script files
PYTHON_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + PYTHON_SCRIPT_FILE_FORMAT
CSHARP_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + CSHARP_SCRIPT_FILE_FORMAT
VB_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + VB_SCRIPT_FILE_FORMAT
RUBY_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + RUBY_SCRIPT_FILE_FORMAT
DYNAMO_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + DYNAMO_SCRIPT_FILE_FORMAT
CONFIG_SCRIPT_POSTFIX = DEFAULT_CONFIG_NAME + PYTHON_SCRIPT_FILE_FORMAT

# Command component defaults
UI_TITLE_PARAM = '__title__'
DOCSTRING_PARAM = '__doc__'
AUTHOR_PARAM = '__author__'

COMMAND_HELP_URL = '__helpurl__'
COMMAND_CONTEXT_PARAM = '__context__'
MIN_REVIT_VERSION_PARAM = '__min_revit_ver__'
MAX_REVIT_VERSION_PARAM = '__max_revit_ver__'
SHIFT_CLICK_PARAM = '__shiftclick__'
BETA_SCRIPT_PARAM = '__beta__'
CLEAN_ENGINE_SCRIPT_PARAM = '__cleanengine__'

LINK_BUTTON_ASSEMBLY_PARAM = '__assembly__'
LINK_BUTTON_COMMAND_CLASS_PARAM = '__commandclass__'

FULLFRAME_ENGINE_PARAM = '__fullframeengine__'

COMMAND_AVAILABILITY_NAME_POSTFIX = 'Availab'
COMP_LIBRARY_DIR_NAME = 'lib'

CTX_SELETION = 'selection'
CTX_ZERODOC = ['zero-doc', 'zerodoc']
