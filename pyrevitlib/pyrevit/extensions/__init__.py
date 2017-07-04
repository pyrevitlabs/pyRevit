# Extension types
# ------------------------------------------------------------------------------
LIB_EXTENSION_POSTFIX = '.lib'
UI_EXTENSION_POSTFIX = '.extension'


# noinspection PyClassHasNoInit
class UIExtensionType:
    ID = 'extension'
    POSTFIX = '.extension'


# noinspection PyClassHasNoInit
class LIBExtensionType:
    ID = 'lib'
    POSTFIX = '.lib'


# noinspection PyClassHasNoInit
class ExtensionTypes:
    UI_EXTENSION = UIExtensionType
    LIB_EXTENSION = LIBExtensionType


# UI_EXTENSION_POSTFIX components
# ------------------------------------------------------------------------------
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

# Component layout elements
DEFAULT_LAYOUT_FILE_NAME = '_layout'
SEPARATOR_IDENTIFIER = '---'
SLIDEOUT_IDENTIFIER = '>>>'

# Component icon
ICON_FILE_FORMAT = '.png'

DEFAULT_ICON_FILE = 'icon' + ICON_FILE_FORMAT
DEFAULT_ON_ICON_FILE = 'on' + ICON_FILE_FORMAT
DEFAULT_OFF_ICON_FILE = 'off' + ICON_FILE_FORMAT

# Command supported languages
PYTHON_LANG = 'python'
CSHARP_LANG = 'csharp'
VB_LANG = 'visualbasic'

# Component scripts
DEFAULT_SCRIPT_NAME = 'script'
PYTHON_SCRIPT_FILE_FORMAT = '.py'
CSHARP_SCRIPT_FILE_FORMAT = '.cs'
VB_SCRIPT_FILE_FORMAT = '.vb'
RUBY_SCRIPT_FILE_FORMAT = '.rb'


PYTHON_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + PYTHON_SCRIPT_FILE_FORMAT
CSHARP_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + CSHARP_SCRIPT_FILE_FORMAT
VB_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + VB_SCRIPT_FILE_FORMAT
RUBY_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + RUBY_SCRIPT_FILE_FORMAT
DEFAULT_CONFIG_SCRIPT_FILE = 'config' + PYTHON_SCRIPT_FILE_FORMAT

# Command component defaults
UI_TITLE_PARAM = '__title__'
DOCSTRING_PARAM = '__doc__'
AUTHOR_PARAM = '__author__'

COMMAND_OPTIONS_PARAM = '__cmdoptions__'
COMMAND_CONTEXT_PARAM = '__context__'
MIN_REVIT_VERSION_PARAM = '__min_revit_ver__'
MAX_REVIT_VERSION_PARAM = '__max_revit_ver__'
SHIFT_CLICK_PARAM = '__shiftclick__'
BETA_SCRIPT_PARAM = '__beta__'

LINK_BUTTON_ASSEMBLY_PARAM = '__assembly__'
LINK_BUTTON_COMMAND_CLASS_PARAM = '__commandclass__'


COMMAND_AVAILABILITY_NAME_POSTFIX = 'Availab'
COMP_LIBRARY_DIR_NAME = 'lib'
