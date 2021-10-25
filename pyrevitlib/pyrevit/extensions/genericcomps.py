"""Generic extension components."""
import os
import os.path as op
import re
import codecs
import copy

from pyrevit import HOST_APP, PyRevitException
from pyrevit import coreutils
from pyrevit.coreutils import yaml
from pyrevit.coreutils import applocales
from pyrevit.coreutils import pyutils
import pyrevit.extensions as exts


#pylint: disable=W0703,C0302,C0103
mlogger = coreutils.logger.get_logger(__name__)


EXT_DIR_KEY = 'directory'
SUB_CMP_KEY = 'components'
LAYOUT_ITEM_KEY = 'layout_items'
LAYOUT_DIR_KEY = 'directive'
TYPE_ID_KEY = 'type_id'
NAME_KEY = 'name'


class TypedComponent(object):
    type_id = None


class CachableComponent(TypedComponent):
    def get_cache_data(self):
        cache_dict = self.__dict__.copy()
        if hasattr(self, TYPE_ID_KEY):
            cache_dict[TYPE_ID_KEY] = getattr(self, TYPE_ID_KEY)
        return cache_dict

    def load_cache_data(self, cache_dict):
        for k, v in cache_dict.items():
            self.__dict__[k] = v


class LayoutDirective(CachableComponent):
    def __init__(self, directive_type=None, target=None):
        self.directive_type = directive_type
        self.target = target


class LayoutItem(CachableComponent):
    def __init__(self, name=None, directive=None):
        self.name = name
        self.directive = directive


class GenericComponent(CachableComponent):
    def __init__(self):
        self.name = None

    def __repr__(self):
        return '<GenericComponent object with name \'{}\'>'.format(self.name)

    @property
    def is_container(self):
        return hasattr(self, '__iter__')


class GenericUIComponent(GenericComponent):
    def __init__(self, cmp_path=None):
        # using classname otherwise exceptions in superclasses won't show
        GenericComponent.__init__(self)
        self.directory = cmp_path
        self.unique_name = self.parent_ctrl_id = None
        self.icon_file = None
        self._ui_title = None
        self._tooltip = self.author = self._help_url = None
        self.media_file = None
        self.min_revit_ver = self.max_revit_ver = None
        self.is_beta = False
        self.highlight_type = None
        self.collapsed = False
        self.version = None

        self.meta = {}
        self.meta_file = None

        self.modules = []
        self.module_paths = []

        self.binary_path = None
        self.library_path = None

        if self.directory:
            self._update_from_directory()

    @classmethod
    def matches(cls, component_path):
        return component_path.lower().endswith(cls.type_id)

    @classmethod
    def make_unique_name(cls, cmp_path):
        """Creates a unique name for the command. This is used to uniquely
        identify this command and also to create the class in
        pyRevit dll assembly. Current method create a unique name based on
        the command full directory address.
        Example:
            for 'pyRevit.extension/pyRevit.tab/Edit.panel/Flip doors.pushbutton'
            unique name would be: 'pyrevit-pyrevit-edit-flipdoors'
        """
        pieces = []
        inside_ext = False
        for dname in cmp_path.split(op.sep):
            if exts.ExtensionTypes.UI_EXTENSION.POSTFIX in dname:
                inside_ext = True

            name, ext = op.splitext(dname)
            if ext != '' and inside_ext:
                pieces.append(name)
            else:
                continue
        return coreutils.cleanup_string(
            exts.UNIQUE_ID_SEPARATOR.join(pieces),
            skip=[exts.UNIQUE_ID_SEPARATOR]
            ).lower()

    def __repr__(self):
        return '<type_id \'{}\' name \'{}\' @ \'{}\'>'\
            .format(self.type_id, self.name, self.directory)

    def _update_from_directory(self):
        self.name = op.splitext(op.basename(self.directory))[0]
        self._ui_title = self.name
        self.unique_name = GenericUIComponent.make_unique_name(self.directory)

        full_file_path = op.join(self.directory, exts.DEFAULT_ICON_FILE)
        self.icon_file = full_file_path if op.exists(full_file_path) else None
        mlogger.debug('Icon file is: %s:%s', self.name, self.icon_file)

        self.media_file = \
            self.find_bundle_file([exts.DEFAULT_MEDIA_FILENAME], finder='name')
        mlogger.debug('Media file is: %s:%s', self.name, self.media_file)

        self._help_url = \
            self.find_bundle_file([exts.HELP_FILE_PATTERN], finder='regex')

        # each component can store custom libraries under
        # lib/ inside the component folder
        lib_path = op.join(self.directory, exts.COMP_LIBRARY_DIR_NAME)
        self.library_path = lib_path if op.exists(lib_path) else None

        # setting up search paths. These paths will be added to
        # all sub-components of this component.
        if self.library_path:
            self.module_paths.append(self.library_path)

        # each component can store custom binaries under
        # bin/ inside the component folder
        bin_path = op.join(self.directory, exts.COMP_BIN_DIR_NAME)
        self.binary_path = bin_path if op.exists(bin_path) else None

        # setting up search paths. These paths will be added to
        # all sub-components of this component.
        if self.binary_path:
            self.module_paths.append(self.binary_path)

        # find meta file
        self.meta_file = self.find_bundle_file([
            exts.BUNDLEMATA_POSTFIX
            ])
        if self.meta_file:
            # sets up self.meta
            try:
                self.meta = yaml.load_as_dict(self.meta_file)
                if self.meta:
                    self._read_bundle_metadata()
            except Exception as err:
                mlogger.error(
                    "Error reading meta file @ %s | %s", self.meta_file, err
                    )

    def _resolve_locale(self, source):
        if isinstance(source, str):
            return source
        elif isinstance(source, dict):
            return applocales.get_locale_string(source)

    def _resolve_liquid_tag(self, param_name, key, value):
        liquid_tag = '{{' + key + '}}'
        exst_val = getattr(self, param_name)
        if exst_val and (liquid_tag in exst_val):   #pylint: disable=E1135
            new_value = exst_val.replace(liquid_tag, value)
            setattr(self, param_name, new_value)

    def _read_bundle_metadata(self):
        self._ui_title = self.meta.get(exts.MDATA_UI_TITLE, self._ui_title)

        self._tooltip = self.meta.get(exts.MDATA_TOOLTIP, self._tooltip)

        # authors could be a list or single value
        self.author = self.meta.get(exts.MDATA_AUTHOR, self.author)
        self.author = self.meta.get(exts.MDATA_AUTHORS, self.author)
        if isinstance(self.author, list):
            self.author = '\n'.join(self.author)

        self._help_url = \
            self.meta.get(exts.MDATA_COMMAND_HELP_URL, self._help_url)

        self.min_revit_ver = \
            self.meta.get(exts.MDATA_MIN_REVIT_VERSION, self.min_revit_ver)
        self.max_revit_ver = \
            self.meta.get(exts.MDATA_MAX_REVIT_VERSION, self.max_revit_ver)

        self.is_beta = \
            self.meta.get(exts.MDATA_BETA_SCRIPT, 'false').lower() == 'true'

        highlight = \
            self.meta.get(exts.MDATA_HIGHLIGHT_KEY, None)
        if highlight and isinstance(highlight, str):
            self.highlight_type = highlight.lower()

        self.collapsed = \
            self.meta.get(exts.MDATA_COLLAPSED_KEY, 'false').lower() == 'true'

        self.modules = \
            self.meta.get(exts.MDATA_LINK_BUTTON_MODULES, self.modules)

    @property
    def control_id(self):
        if self.parent_ctrl_id:
            return self.parent_ctrl_id + '%{}'.format(self.name)
        else:
            return "CustomCtrl_%CustomCtrl_%{}".format(self.name)

    @property
    def ui_title(self):
        return self._resolve_locale(self._ui_title)

    @property
    def tooltip(self):
        return self._resolve_locale(self._tooltip)

    @property
    def help_url(self):
        return self._resolve_locale(self._help_url)

    @property
    def is_supported(self):
        if self.min_revit_ver:
            # If host is older than the minimum host version, raise exception
            if int(HOST_APP.version) < int(self.min_revit_ver):
                mlogger.debug('Requires min version: %s', self.min_revit_ver)
                return False
        if self.max_revit_ver:
            # If host is newer than the max host version, raise exception
            if int(HOST_APP.version) > int(self.max_revit_ver):
                mlogger.debug('Requires max version: %s', self.max_revit_ver)
                return False
        return True

    def get_full_bundle_name(self):
        return self.name + self.type_id

    def has_module_path(self, path):
        return path in self.module_paths

    def add_module_path(self, path):
        if path and not self.has_module_path(path):
            mlogger.debug('Appending syspath: %s to %s', path, self)
            self.module_paths.append(path)

    def remove_module_path(self, path):
        if path and self.has_module_path(path):
            mlogger.debug('Removing syspath: %s from %s', path, self)
            return self.module_paths.remove(path)

    def get_bundle_file(self, file_name):
        if self.directory and file_name:
            file_addr = op.join(self.directory, file_name)
            return file_addr if op.exists(file_addr) else None

    def find_bundle_file(self, patterns, finder='postfix'):
        if self.directory:
            for bundle_file in os.listdir(self.directory):
                if 'name' == finder:
                    for file_name in patterns:
                        if op.splitext(bundle_file)[0] == file_name:
                            return op.join(self.directory, bundle_file)
                elif 'postfix' == finder:
                    for file_postfix in patterns:
                        if bundle_file.endswith(file_postfix):
                            return op.join(self.directory, bundle_file)
                elif 'regex' == finder:
                    for regex_pattern in patterns:
                        if re.match(regex_pattern, bundle_file):
                            return op.join(self.directory, bundle_file)
        return None

    def find_bundle_module(self, module, by_host=False):
        # test of file_name is an actually path to a file
        if op.isfile(module):
            return module

        def build_assm_filename(module_filename):
            # build assembly by host version (assm_file_2020.ext)
            assm_name, assm_ext = op.splitext(module_filename)
            return assm_name + '_' + HOST_APP.version + assm_ext

        if by_host:
            module = build_assm_filename(module)

        # test if module is inside search paths
        for module_path in self.module_paths:
            possible_module_path = op.join(module_path, module)
            if op.isfile(possible_module_path):
                return possible_module_path

    def configure(self, config_dict):
        configurable_params = \
            ['_ui_title', '_tooltip', '_help_url', 'author']
        # get root key:value pairs
        for key, value in config_dict.items():
            for param_name in configurable_params:
                self._resolve_liquid_tag(param_name, key, value)
        # get key:value pairs grouped under special key, if exists
        templates = config_dict.get(exts.MDATA_TEMPLATES_KEY, {})
        for key, value in templates.items():
            for param_name in configurable_params:
                self._resolve_liquid_tag(param_name, key, value)


# superclass for all UI group items (tab, panel, button groups, stacks)
class GenericUIContainer(GenericUIComponent):
    allowed_sub_cmps = []

    def __init__(self, cmp_path=None):
        self.layout_items = []
        self.components = []
        # using classname otherwise exceptions in superclasses won't show
        GenericUIComponent.__init__(self, cmp_path=cmp_path)

    def _update_from_directory(self):
        # using classname otherwise exceptions in superclasses won't show
        GenericUIComponent._update_from_directory(self)
        # process layout
        # default is layout in metadata, the older layout file is deprecate
        # and is for fallback only
        if not self.parse_layout_metadata():
            mlogger.debug('Container does not have layout file defined: %s',
                self)


    def _apply_layout_directive(self, directive, component):
        # if matching directive found, process the directive
        if directive.directive_type == 'title':
            component._ui_title = directive.target

    def __iter__(self):
        # if item is not listed in layout, it will not be created
        if self.layout_items:
            mlogger.debug('Reordering components per layout file...')
            laidout_cmps = []
            for litem in self.layout_items:
                matching_cmp = \
                        next((x for x in self.components
                              if x.name == litem.name), None)
                if matching_cmp:
                    # apply directives before adding to list
                    if litem.directive:
                        self._apply_layout_directive(litem.directive,
                                                     matching_cmp)
                    laidout_cmps.append(matching_cmp)

            # insert separators and slideouts per layout definition
            mlogger.debug('Adding separators and slide outs per layout...')
            last_item_index = len(self.layout_items) - 1
            for idx, litem in enumerate(self.layout_items):
                if exts.SEPARATOR_IDENTIFIER in litem.name \
                        and idx < last_item_index:
                    separator = GenericUIComponent()
                    separator.type_id = exts.SEPARATOR_IDENTIFIER
                    laidout_cmps.insert(idx, separator)
                elif exts.SLIDEOUT_IDENTIFIER in litem.name \
                        and idx < last_item_index:
                    slideout = GenericUIComponent()
                    slideout.type_id = exts.SLIDEOUT_IDENTIFIER
                    laidout_cmps.insert(idx, slideout)

            mlogger.debug('Reordered sub_component list is: %s', laidout_cmps)
            return laidout_cmps
        else:
            return self.components

    def parse_layout_directive(self, layout_line):
        parts = re.findall(r'(.+)\[(.+):(.*)\]', layout_line)
        if parts:
            source_item, directive, target_value = parts[0]
            # cleanup values
            directive = directive.lower().strip()
            target_value = target_value.strip()
            # process any escape characters in target value
            # https://stackoverflow.com/a/4020824/2350244
            # decode('string_escape') for python 2
            target_value = \
                target_value.encode('utf-8').decode('string_escape')
            # create directive obj
            return source_item, LayoutDirective(directive_type=directive,
                                                target=target_value)
        return layout_line, None

    def parse_layout_item(self, layout_line):
        if layout_line:
            layout_item_name, layout_item_drctv = \
                self.parse_layout_directive(layout_line)
            return LayoutItem(name=layout_item_name,
                              directive=layout_item_drctv)

    def parse_layout_items(self, layout_lines):
        for layout_line in layout_lines:
            layout_item = self.parse_layout_item(layout_line)
            if layout_item:
                self.layout_items.append(layout_item)
        mlogger.debug('Layout is: %s', self.layout_items)

    def parse_layout_metadata(self):
        layout = self.meta.get(exts.MDATA_LAYOUT, [])
        if layout:
            self.parse_layout_items(layout)
            return True

    def contains(self, item_name):
        return any([x.name == item_name for x in self.components])

    def add_module_path(self, path):
        if path and not self.has_module_path(path):
            mlogger.debug('Appending syspath: %s to %s', path, self)
            for component in self.components:
                component.add_module_path(path)
            self.module_paths.append(path)

    def remove_module_path(self, path):
        if path and self.has_module_path(path):
            mlogger.debug('Removing syspath: %s from %s', path, self)
            for component in self.components:
                component.remove_module_path(path)
            return self.module_paths.remove(path)

    def add_component(self, comp):
        # set search paths
        for path in self.module_paths:
            comp.add_module_path(path)
        # set its own control id on the child component
        if hasattr(comp, 'parent_ctrl_id'):
            comp.parent_ctrl_id = self.control_id
        # now add to list
        self.components.append(comp)

    def find_components_of_type(self, cmp_type):
        sub_comp_list = []
        for sub_comp in self.components:
            if isinstance(sub_comp, cmp_type):
                sub_comp_list.append(sub_comp)
            elif sub_comp.is_container:
                sub_comp_list.extend(sub_comp.find_components_of_type(cmp_type))

        return sub_comp_list

    def find_layout_items(self):
        layout_items = []
        layout_items.extend(self.layout_items)
        for sub_comp in self.components:
            if sub_comp.is_container:
                layout_items.extend(sub_comp.find_layout_items())
        return layout_items

    def configure(self, config_dict):
        # update self meta
        GenericUIComponent.configure(self, config_dict=config_dict)
        # create an updated dict to pass to children
        updated_dict = copy.deepcopy(config_dict)
        updated_dict = pyutils.merge(updated_dict, self.meta)
        # replace the meta values with the expanded values
        # so children can use the expanded
        updated_dict[exts.MDATA_UI_TITLE] = self.ui_title
        updated_dict[exts.MDATA_TOOLTIP] = self.tooltip
        updated_dict[exts.MDATA_COMMAND_HELP_URL] = self.help_url
        updated_dict[exts.AUTHOR_PARAM] = self.author
        if exts.AUTHORS_PARAM in updated_dict:
            updated_dict.pop(exts.AUTHORS_PARAM)
        for component in self:
            component.configure(updated_dict)

# superclass for all single command classes (link, push button, toggle button)
# GenericUICommand is not derived from GenericUIContainer since a command
# can not contain other elements
class GenericUICommand(GenericUIComponent):
    """Superclass for all single commands.
    The information provided by these classes will be used to create a
    push button under Revit UI. However, pyRevit expands the capabilities of
    push button beyond what is provided by Revit UI. (e.g. Toggle button
    changes it's icon based on its on/off status)
    See LinkButton and ToggleButton classes.
    """
    def __init__(self, cmp_path=None, needs_script=True):
        self.needs_script = needs_script
        self.script_file = self.config_script_file = None
        self.arguments = []
        self.context = None
        self.class_name = self.avail_class_name = None
        self.requires_clean_engine = False
        self.requires_fullframe_engine = False
        self.requires_persistent_engine = False
        self.requires_mainthread_engine = False
        # engine options specific to dynamo
        self.dynamo_path = None
        # self.dynamo_path_exec = False
        self.dynamo_path_check_existing = False
        self.dynamo_force_manual_run = False
        self.dynamo_model_nodes_info = None
        # using classname otherwise exceptions in superclasses won't show
        GenericUIComponent.__init__(self, cmp_path=cmp_path)

        mlogger.debug('Maximum host version: %s', self.max_revit_ver)
        mlogger.debug('Minimum host version: %s', self.min_revit_ver)
        mlogger.debug('command tooltip: %s', self._tooltip)
        mlogger.debug('Command author: %s', self.author)
        mlogger.debug('Command help url: %s', self._help_url)

        if self.is_beta:
            mlogger.debug('Command is in beta.')

    def _update_from_directory(self):
        # using classname otherwise exceptions in superclasses won't show
        GenericUIComponent._update_from_directory(self)

        # find script file
        self.script_file = \
            self.find_bundle_file([
                exts.PYTHON_SCRIPT_POSTFIX,
                exts.CSHARP_SCRIPT_POSTFIX,
                exts.VB_SCRIPT_POSTFIX,
                exts.RUBY_SCRIPT_POSTFIX,
                exts.DYNAMO_SCRIPT_POSTFIX,
                exts.GRASSHOPPER_SCRIPT_POSTFIX,
                exts.GRASSHOPPERX_SCRIPT_POSTFIX,
                ])

        if self.needs_script and not self.script_file:
            mlogger.error('Command %s: Does not have script file.', self)

        # if python
        if self.script_language == exts.PYTHON_LANG:
            # allow python tools to load side scripts
            self.add_module_path(self.directory)
            # read the metadata from python script if not metadata file
            if not self.meta and not self.is_cpython:
                # sets up self.meta from script global variables
                self._read_bundle_metadata_from_python_script()

        # find config scripts
        self.config_script_file = \
            self.find_bundle_file([
                exts.PYTHON_CONFIG_SCRIPT_POSTFIX,
                exts.CSHARP_CONFIG_SCRIPT_POSTFIX,
                exts.VB_CONFIG_SCRIPT_POSTFIX,
                exts.RUBY_CONFIG_SCRIPT_POSTFIX,
                exts.DYNAMO_CONFIG_SCRIPT_POSTFIX,
                exts.GRASSHOPPER_CONFIG_SCRIPT_POSTFIX,
                exts.GRASSHOPPERX_CONFIG_SCRIPT_POSTFIX,
                ])

        if not self.config_script_file:
            mlogger.debug(
                'Command %s: Does not have independent config script.',
                self)
            self.config_script_file = self.script_file

    def _read_bundle_metadata(self):
        # using classname otherwise exceptions in superclasses won't show
        GenericUIComponent._read_bundle_metadata(self)
        # determine engine configs
        if exts.MDATA_ENGINE in self.meta:
            self.requires_clean_engine = \
                self.meta[exts.MDATA_ENGINE].get(
                    exts.MDATA_ENGINE_CLEAN, 'false').lower() == 'true'
            self.requires_fullframe_engine = \
                self.meta[exts.MDATA_ENGINE].get(
                    exts.MDATA_ENGINE_FULLFRAME, 'false').lower() == 'true'
            self.requires_persistent_engine = \
                self.meta[exts.MDATA_ENGINE].get(
                    exts.MDATA_ENGINE_PERSISTENT, 'false').lower() == 'true'

            # determine if engine is required to run on main thread
            # MDATA_ENGINE_MAINTHREAD is the generic option
            rme = self.meta[exts.MDATA_ENGINE].get(
                exts.MDATA_ENGINE_MAINTHREAD, 'false') == 'true'
            # MDATA_ENGINE_DYNAMO_AUTOMATE is specific naming for dynamo
            automate = self.meta[exts.MDATA_ENGINE].get(
                exts.MDATA_ENGINE_DYNAMO_AUTOMATE, 'false') == 'true'
            self.requires_mainthread_engine = rme or automate

            # process engine options specific to dynamo
            self.dynamo_path = \
                self.meta[exts.MDATA_ENGINE].get(
                    exts.MDATA_ENGINE_DYNAMO_PATH, None)
            # self.dynamo_path_exec = \
            #     self.meta[exts.MDATA_ENGINE].get(
            #         exts.MDATA_ENGINE_DYNAMO_PATH_EXEC, 'true') == 'true'
            self.dynamo_path_check_existing = \
                self.meta[exts.MDATA_ENGINE].get(
                    exts.MDATA_ENGINE_DYNAMO_PATH_CHECK_EXIST,
                    'false') == 'true'
            self.dynamo_force_manual_run = \
                self.meta[exts.MDATA_ENGINE].get(
                    exts.MDATA_ENGINE_DYNAMO_FORCE_MANUAL_RUN,
                    'false') == 'true'
            self.dynamo_model_nodes_info = \
                self.meta[exts.MDATA_ENGINE].get(
                    exts.MDATA_ENGINE_DYNAMO_MODEL_NODES_INFO, None)

        # panel buttons should be active always
        if self.type_id == exts.PANEL_PUSH_BUTTON_POSTFIX:
            self.context = self._parse_context_directives(exts.CTX_ZERODOC)
        else:
            self.context = \
                self.meta.get(exts.MDATA_COMMAND_CONTEXT, None)
            if self.context:
                self.context = self._parse_context_directives(self.context)

    def _parse_context_list(self, context):
        context_rules = []

        str_items = [x for x in context if isinstance(x, str)]
        context_rules.append(
            exts.MDATA_COMMAND_CONTEXT_RULE.format(
                rule=exts.MDATA_COMMAND_CONTEXT_ALL_SEP.join(str_items)
                )
        )

        dict_items = [x for x in context if isinstance(x, dict)]
        for ditem in dict_items:
            context_rules.extend(self._parse_context_dict(ditem))

        return context_rules

    def _parse_context_dict(self, context):
        context_rules = []
        for ctx_key, ctx_value in context.items():
            if ctx_key == exts.MDATA_COMMAND_CONTEXT_TYPE:
                context_type = (
                    exts.MDATA_COMMAND_CONTEXT_ANY_SEP
                    if ctx_value == exts.MDATA_COMMAND_CONTEXT_ANY
                    else exts.MDATA_COMMAND_CONTEXT_ALL_SEP
                )
                continue

            if isinstance(ctx_value, str):
                ctx_value = [ctx_value]

            key = ctx_key.lower()
            condition = ""
            # all
            if key == exts.MDATA_COMMAND_CONTEXT_ALL \
                    or key == exts.MDATA_COMMAND_CONTEXT_NOTALL:
                condition = exts.MDATA_COMMAND_CONTEXT_ALL_SEP

            # any
            elif key == exts.MDATA_COMMAND_CONTEXT_ANY \
                    or key == exts.MDATA_COMMAND_CONTEXT_NOTANY:
                condition = exts.MDATA_COMMAND_CONTEXT_ANY_SEP

            # except
            elif key == exts.MDATA_COMMAND_CONTEXT_EXACT \
                    or key == exts.MDATA_COMMAND_CONTEXT_NOTEXACT:
                condition = exts.MDATA_COMMAND_CONTEXT_EXACT_SEP

            context = condition.join(
                [x for x in ctx_value if isinstance(x, str)]
                )
            formatted_rule = \
                exts.MDATA_COMMAND_CONTEXT_RULE.format(rule=context)
            if key.startswith(exts.MDATA_COMMAND_CONTEXT_NOT):
                formatted_rule = "!" + formatted_rule
            context_rules.append(formatted_rule)
        return context_rules

    def _parse_context_directives(self, context):
        context_rules = []

        if isinstance(context, str):
            context_rules.append(
                exts.MDATA_COMMAND_CONTEXT_RULE.format(rule=context)
            )
        elif isinstance(context, list):
            context_rules.extend(self._parse_context_list(context))

        elif isinstance(context, dict):
            if "rule" in context:
                return context["rule"]
            context_rules.extend(self._parse_context_dict(context))

        context_type = exts.MDATA_COMMAND_CONTEXT_ALL_SEP
        return context_type.join(context_rules)

    def _read_bundle_metadata_from_python_script(self):
        try:
            # reading script file content to extract parameters
            script_content = \
                coreutils.ScriptFileParser(self.script_file)

            self._ui_title = \
                script_content.extract_param(exts.UI_TITLE_PARAM) \
                    or self._ui_title

            script_docstring = script_content.get_docstring()
            custom_docstring = \
                script_content.extract_param(exts.DOCSTRING_PARAM)
            self._tooltip = \
                custom_docstring or script_docstring or self._tooltip

            script_author = script_content.extract_param(exts.AUTHOR_PARAM)
            script_author = script_content.extract_param(exts.AUTHORS_PARAM)
            if isinstance(script_author, list):
                script_author = '\n'.join(script_author)
            self.author = script_author or self.author

            # extracting min requried Revit and pyRevit versions
            self.max_revit_ver = \
                script_content.extract_param(exts.MAX_REVIT_VERSION_PARAM) \
                    or self.max_revit_ver
            self.min_revit_ver = \
                script_content.extract_param(exts.MIN_REVIT_VERSION_PARAM) \
                    or self.min_revit_ver
            self._help_url = \
                script_content.extract_param(exts.COMMAND_HELP_URL_PARAM) \
                    or self._help_url

            self.is_beta = \
                script_content.extract_param(exts.BETA_SCRIPT_PARAM) \
                    or self.is_beta

            self.highlight_type = \
                script_content.extract_param(exts.HIGHLIGHT_SCRIPT_PARAM) \
                    or self.highlight_type

            # only True when command is specifically asking for
            # a clean engine or a fullframe engine. False if not set.
            self.requires_clean_engine = \
                script_content.extract_param(exts.CLEAN_ENGINE_SCRIPT_PARAM) \
                    or False
            self.requires_fullframe_engine = \
                script_content.extract_param(exts.FULLFRAME_ENGINE_PARAM) \
                    or False
            self.requires_persistent_engine = \
                script_content.extract_param(exts.PERSISTENT_ENGINE_PARAM) \
                    or False

            # panel buttons should be active always
            if self.type_id == exts.PANEL_PUSH_BUTTON_POSTFIX:
                self.context = self._parse_context_directives(exts.CTX_ZERODOC)
            else:
                self.context = \
                    script_content.extract_param(exts.COMMAND_CONTEXT_PARAM)
                if self.context:
                    self.context = self._parse_context_directives(self.context)

        except Exception as parse_err:
            mlogger.log_parse_except(self.script_file, parse_err)

    @property
    def script_language(self):
        if self.script_file is not None:
            if self.script_file.endswith(exts.PYTHON_SCRIPT_FILE_FORMAT):
                return exts.PYTHON_LANG
            elif self.script_file.endswith(exts.CSHARP_SCRIPT_FILE_FORMAT):
                return exts.CSHARP_LANG
            elif self.script_file.endswith(exts.VB_SCRIPT_FILE_FORMAT):
                return exts.VB_LANG
            elif self.script_file.endswith(exts.RUBY_SCRIPT_FILE_FORMAT):
                return exts.RUBY_LANG
            elif self.script_file.endswith(exts.DYNAMO_SCRIPT_FILE_FORMAT):
                return exts.DYNAMO_LANG
            elif self.script_file.endswith(
                    exts.GRASSHOPPER_SCRIPT_FILE_FORMAT) \
                    or self.script_file.endswith(
                        exts.GRASSHOPPERX_SCRIPT_FILE_FORMAT
                    ):
                return exts.GRASSHOPPER_LANG
        else:
            return None

    @property
    def control_id(self):
        if self.parent_ctrl_id:
            return self.parent_ctrl_id + '%{}'.format(self.name)
        else:
            return '%{}'.format(self.name)

    @property
    def is_cpython(self):
        with open(self.script_file, 'r') as script_f:
            return exts.CPYTHON_HASHBANG in script_f.readline()

    def has_config_script(self):
        return self.config_script_file != self.script_file
