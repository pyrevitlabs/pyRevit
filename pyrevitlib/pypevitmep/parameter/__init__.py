# coding: utf8

import os
import csv

from System import Guid

from Autodesk.Revit.DB import ParameterType, DefinitionFile, DefinitionGroup, InstanceBinding, \
    ExternalDefinition, ExternalDefinitionCreationOptions, Definition, \
    ElementBinding, Category, LabelUtils, BuiltInParameterGroup, DefinitionBindingMapIterator, Document

import rpw
from rpw import revit
from pyrevit.forms import alert

# from manageshared import ManageSharedParameter


class SharedParameter:
    """
    Class used to manage Revit shared parameters
    :param name: Displayed shared parameter name
    :param group: Group used in parameter definition file (shared parameter file)
    :param type : Parameter type like Text, PipingFlow etc…
    :param guid: Parameter globally unique identifier
    :param description: Parameter description hint
    :param user_modifiable: This property indicates whether this parameter can be modified by UI user or not.
    :param visible: If false parameter is stored without being visible.
    """
    def __init__(self, name, ptype, group="pypevitmep", guid=None,
                 description="", modifiable=True, visible=True, new=True):
        # type: (str, ParameterType or str, str, Guid or None, str, bool, bool, bool) -> None

        self.name = name
        self.description = description
        self.group = group

        true_tuple = (True, "", None, "True", "Yes", "Oui", 1)

        if modifiable in true_tuple:
            self.modifiable = True
        else:
            self.modifiable = False

        if visible in true_tuple:
            self.visible = True
        else:
            self.visible = False

        # Check if a Guid is given. If not a new one is created
        if not guid:
            self.guid = Guid.NewGuid()
        else:
            self.guid = guid
        # Check if given parameter type is valid. If not user is prompted to choose one.
        if isinstance(ptype, ParameterType):
            self.type = ptype
        else:
            try:
                self.type = getattr(ParameterType, ptype)
            except AttributeError:
                selected_type = rpw.ui.forms.SelectFromList(
                    "Select ParameterType",
                    ParameterType.GetNames(ParameterType),
                    "Parameter {} ParameterType: {} is not valid. Please select a parameter type".format(name, ptype),
                    sort=False)
                self.type = getattr(ParameterType, selected_type)

        self.initial_values = {}
        if new is True:
            self.new = new
        else:
            self.new = False
            self.initial_values_update()

        self.changed = False

    def __repr__(self):
        return "<{}> {} {}".format(self.__class__.__name__, self.name, self.guid)

    @classmethod
    def get_definition_file(cls):
        # type: () -> DefinitionFile
        definition_file = revit.app.OpenSharedParameterFile()
        if not definition_file:
            cls.change_definition_file()
        return definition_file

    def get_definitiongroup(self, definition_file=None):
        # type: (DefinitionFile) -> DefinitionGroup
        if not definition_file:
            definition_file = self.get_definition_file()
        return definition_file.Groups[self.group]

    def get_definition(self):
        return self.get_definitiongroup().Definitions[self.name]

    @classmethod
    def get_definition_by_name(cls, name):
        for group in cls.get_definition_file().Groups:  # type: DefinitionGroup
            for definition in group.Definitions:  # type: Definition
                if definition.Name == name:
                    return definition

    def initial_values_update(self):
        self.initial_values = {"name": self.name, "type": self.type, "group": self.group,
                               "guid": self.guid, "description": self.description, "modifiable": self.modifiable,
                               "visible": self.visible}

    @staticmethod
    def read_from_csv(csv_path=None):
        """
        Retrieve shared parameters from a csv file.
        csv file need to be formatter this way :
        <Parameter Name>, <ParameterType>, <DefinitionGroup>, (Optional)<Guid>,(Optional)<Description>,
        (Optional)<UserModifiable> True or False, (Optional)<Visible> True or False
        :param csv_path: absolute path to csv file
        """
        if not csv_path:
            csv_path = rpw.ui.forms.select_file(extensions='csv Files (*.csv*)|*.csv*', title='Select File',
                                                multiple=False, restore_directory=True)
            if not csv_path:
                raise ValueError("No file selected")
        shared_parameter_list = []

        with open(csv_path, "r") as csv_file:
            file_reader = csv.reader(csv_file)
            file_reader.next()

            for row in file_reader:
                shared_parameter_list.append(SharedParameter(*row, new=False))

        return shared_parameter_list

    @classmethod
    def read_from_definition_file(cls, definition_groups=None, definition_names=None, definition_file=None):
        # type: (list, list, DefinitionFile) -> list
        """
        Retrieve definitions from a definition file
        """
        if not definition_groups:
            definition_groups = []

        if not definition_names:
            definition_names = []

        if not definition_file:
            definition_file = cls.get_definition_file()

        shared_parameter_list = []

        for dg in definition_file.Groups:
            if definition_groups and dg.Name not in (dg.Name for dg in definition_groups):
                continue
            for definition in dg.Definitions:
                if definition_names and definition.Name not in definition_names:
                    continue
                shared_parameter_list.append(cls(definition.Name,
                                                 definition.ParameterType,
                                                 dg.Name,
                                                 definition.GUID,
                                                 definition.Description,
                                                 definition.UserModifiable,
                                                 definition.Visible,
                                                 False
                                                 )
                                             )

        return shared_parameter_list

    def write_to_definition_file(self, definition_file=None, warning=True):
        # type: (DefinitionFile, bool) -> ExternalDefinition
        """
        Create a new parameter definition in current shared parameter file
        :param definition_file: (Optional) definition file
        :param warning: (Optional) Warn user if a definition with given name already exist
        :return: External definition which have just been written
        """
        if not definition_file:
            definition_file = self.get_definition_file()

        if not self.group:
            self.group = "pypevitmep"

        definition_group = definition_file.Groups[self.group]
        if not definition_group:
            definition_group = definition_file.Groups.Create(self.group)

        if definition_group.Definitions[self.name] and warning:
            alert("A parameter definition named {} already exist".format(self.name))
            return
        else:
            external_definition_create_options = ExternalDefinitionCreationOptions(self.name,
                                                                                   self.type,
                                                                                   GUID=self.guid,
                                                                                   UserModifiable=self.modifiable,
                                                                                   Description=self.description,
                                                                                   Visible=self.visible)
            definition = definition_group.Definitions.Create(external_definition_create_options)
        self.initial_values_update()
        self.new = self.changed = False
        return

    @staticmethod
    def delete_from_definition_file(shared_parameters, definition_file=None, warning=True):
        # type: (List[SharedParameter], DefinitionFile, bool) -> None
        if definition_file is None:
            definition_file = SharedParameter.get_definition_file()
        file_path = definition_file.Filename
        tmp_file_path = "{}.tmp".format(file_path)

        with open(file_path, 'r') as file, open(tmp_file_path, 'wb') as file_tmp:
            group_dict = {}
            for line in file:
                row = line.strip("\n").strip("\x00").strip("\r").decode('utf-16').split("\t")
                if row[0] == "GROUP":
                    group_dict[row[1]] = row[2]
                    file_tmp.write(line)
                elif row[0] == "PARAM":
                    for definition in shared_parameters:
                        if row[2] == definition.name and group_dict[row[5]] == definition.group:
                            break
                    else:
                        file_tmp.write(line)
                else:
                    file_tmp.write(line)

        # Remove temp files and rename modified file to original file name
        os.remove(file_path)
        os.rename(tmp_file_path, file_path)

    @staticmethod
    def create_definition_file(path_and_name=None):
        """Create a new DefinitionFile to store SharedParameter definitions
        :param path_and_name: file path and name including extension (.txt file)
        :rtype: DefinitionFile
        """
        if path_and_name is None:
            path = rpw.ui.forms.select_folder()
            path_and_name = rpw.ui.forms.TextInput("name", r"{}\pyrevitmep_sharedparameters.txt".format(path), False)
        with open(path_and_name, "w"):
            pass
        rpw.revit.app.SharedParametersFilename = path_and_name
        return rpw.revit.app.OpenSharedParameterFile()

    @classmethod
    def change_definition_file(cls):
        rpw.revit.app.SharedParametersFilename = rpw.ui.forms.select_file()
        rpw.revit.app.OpenSharedParameterFile()
        return cls.get_definition_file()


class ProjectParameter:
    def __init__(self, definition, binding):
        # type: (Definition, ElementBinding) -> None
        self.definition = definition
        self.binding = binding
        self.category_set = binding.Categories
        self.bip_group =  BipGroup(definition.ParameterGroup)
        self.pt_name = LabelUtils.GetLabelFor(definition.ParameterType)
        self.ut_name = LabelUtils.GetLabelFor(definition.UnitType)
        if isinstance(binding, InstanceBinding):
            self.is_instance = True
        else:
            self.is_instance = False

    def __repr__(self):
            return "<{}> {}".format(self.__class__.__name__, self.definition.Name)

    @property
    def name(self):
        return self.definition.Name

    @property
    def parameter_type(self):
        return self.definition.ParameterType

    @property
    def unit_type(self):
        return self.definition.UnitType

    @classmethod
    def read_from_revit_doc(cls, doc=revit.doc):
        # type: (Document) -> iter
        """Generator which return all ProjectParameter in document"""
        iterator = doc.ParameterBindings.ForwardIterator()  # type: DefinitionBindingMapIterator
        for binding in iterator:  # type: ElementBinding
            definition = iterator.Key
            yield cls(definition, binding)

    def save_to_revit_doc(self, doc=revit.doc):
        """Save current project parameter to Revit doc.
        Need to be used in an open Transaction. """
        bindingmap = doc.ParameterBindings # type: BindingMap
        if bindingmap[self.definition]:
            bindingmap.ReInsert(self.definition, self.binding, self.bip_group.bip_group)
        else:
            bindingmap.Insert(self.definition, self.binding, self.bip_group.bip_group)

    # @classmethod
    # def new_from_shared_parameters(cls, instance=True, app=revit.app):
    #     if instance:
    #         binding = app.Create.NewInstanceBinding()  # type: ElementBinding
    #     else:
    #         binding = app.Create.NewTypeBinding()  # type: ElementBinding
    #     for category in ProjectParameter.bound_allowed_category_generator():
    #         binding.Categories.Insert(category)
    #     for definition in ManageSharedParameter.show_dialog():
    #         yield cls(definition, binding)

    @staticmethod
    def all_categories():
        category_set = revit.app.Create.NewCategorySet()
        for category in revit.doc.Settings.Categories:
            if category.AllowsBoundParameters:
                category_set.Insert(category)
        return category_set

    @staticmethod
    def bound_allowed_category_generator():
        for category in revit.doc.Settings.Categories:
            if category.AllowsBoundParameters:
                yield category


class BoundAllowedCategory:
    def __init__(self, category):
        # type: (Category) -> None
        self.category = category
        self.is_bound = False

    @property
    def name(self):
        return self.category.Name

    @property
    def category_type(self):
        return self.category.CategoryType

class BipGroup:
    def __init__(self, bip_group):
        # type: (BuiltInParameterGroup) -> None
        """BuiltInParameterGroup wrapper"""
        self.bip_group = bip_group

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        try:
            return self.bip_group == other.bip_group
        except AttributeError:
            return False

    def __gt__(self, other):
        return self.name > other.name

    def __lt__(self, other):
        return self.name < other.name

    @property
    def name(self):
        return LabelUtils.GetLabelFor(self.bip_group)

    @staticmethod
    def bip_group_generator():
        for builtinparametergroup in BuiltInParameterGroup.GetValues(BuiltInParameterGroup):
            yield builtinparametergroup  # type: BuiltInParameterGroup

    @classmethod
    def bip_group_name_generator(cls):
        for builtinparametergroup in cls.bip_group_generator():
            yield LabelUtils.GetLabelFor(builtinparametergroup)

    @classmethod
    def bip_group_by_name(cls, name):
        # type: (str) -> BuiltInParameterGroup
        for bip_group in cls.bip_group_generator():
            if LabelUtils.GetLabelFor(bip_group) == name:
                return bip_group
