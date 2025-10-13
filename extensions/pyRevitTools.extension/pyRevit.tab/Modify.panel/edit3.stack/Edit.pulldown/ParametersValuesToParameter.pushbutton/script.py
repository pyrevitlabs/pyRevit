# -*- coding: utf-8 -*-
"""
Script to copy parameter values from selected parameters to a target parameter
for elements in a selected category using XAML UI.
"""
import clr

clr.AddReference("PresentationFramework")

from System.Collections.Generic import List
from System import ArgumentException, NullReferenceException
from pyrevit import revit, DB, forms, HOST_APP, script


def get_localized_texts():
    """Get localized texts based on Revit's UI language."""
    revit_language_enum = HOST_APP.language
    revit_language = str(revit_language_enum)

    # Translation dictionaries using simple language names as keys
    translations = {
        "English": {
            "window_title": "Params2Param - Copy Parameter Values",
            "select_category": "Select Category:",
            "source_parameters": "Source Parameters (Select Multiple if needed):",
            "target_parameter": "Target Parameter (Select One):",
            "execute": "Execute",
            "cancel": "Cancel",
            "invalid_category": "Invalid category selected",
            "no_elements": "No elements found",
            "select_category_error": "Please select a category",
            "no_elements_error": "No elements found for selected category",
            "select_source_error": "Please select at least one source parameter",
            "select_target_error": "Please select a target parameter",
            "elements_updated": "{} elements updated with parameter values from [{}] to '{}' parameter",
            "elements_failed": "{} elements failed to update.",
        },
        "French": {
            "window_title": "Params2Param - Copier les Valeurs de Paramètres",
            "select_category": "Sélectionner la Catégorie:",
            "source_parameters": "Paramètres Source (Sélectionnez-en Plusieurs Si Nécessaire):",
            "target_parameter": "Paramètre Cible (Sélectionnez-en Un Seul):",
            "execute": "Exécuter",
            "cancel": "Annuler",
            "invalid_category": "Catégorie sélectionnée invalide",
            "no_elements": "Aucun élément trouvé",
            "select_category_error": "Veuillez sélectionner une catégorie",
            "no_elements_error": "Aucun élément trouvé pour la catégorie sélectionnée",
            "select_source_error": "Veuillez sélectionner au moins un paramètre source",
            "select_target_error": "Veuillez sélectionner un paramètre cible",
            "elements_updated": "{} éléments mis à jour avec les valeurs de paramètres de [{}] vers le paramètre '{}'",
            "elements_failed": "{} éléments n'ont pas pu être mis à jour.",
        },
        "German": {
            "window_title": "Params2Param - Parameterwerte kopieren",
            "select_category": "Kategorie auswählen:",
            "source_parameters": "Quellparameter (Mehrere auswählen falls nötig):",
            "target_parameter": "Zielparameter (Einen auswählen):",
            "execute": "Ausführen",
            "cancel": "Abbrechen",
            "invalid_category": "Ungültige Kategorie ausgewählt",
            "no_elements": "Keine Elemente gefunden",
            "select_category_error": "Bitte wählen Sie eine Kategorie",
            "no_elements_error": "Keine Elemente für die ausgewählte Kategorie gefunden",
            "select_source_error": "Bitte wählen Sie mindestens einen Quellparameter",
            "select_target_error": "Bitte wählen Sie einen Zielparameter",
            "elements_updated": "{} Elemente mit Parameterwerten von [{}] zum Parameter '{}' aktualisiert",
            "elements_failed": "{} Elemente konnten nicht aktualisiert werden.",
        },
        "Spanish": {
            "window_title": "Params2Param - Copiar Valores de Parámetros",
            "select_category": "Seleccionar Categoría:",
            "source_parameters": "Parámetros Fuente (Seleccionar Múltiples si es necesario):",
            "target_parameter": "Parámetro Objetivo (Seleccionar Uno):",
            "execute": "Ejecutar",
            "cancel": "Cancelar",
            "invalid_category": "Categoría seleccionada inválida",
            "no_elements": "No se encontraron elementos",
            "select_category_error": "Por favor seleccione una categoría",
            "no_elements_error": "No se encontraron elementos para la categoría seleccionada",
            "select_source_error": "Por favor seleccione al menos un parámetro fuente",
            "select_target_error": "Por favor seleccione un parámetro objetivo",
            "elements_updated": "{} elementos actualizados con valores de parámetros de [{}] al parámetro '{}'",
            "elements_failed": "{} elementos no pudieron ser actualizados.",
        },
        "Russian": {
            "window_title": "Params2Param - Копирование Значений Параметров",
            "select_category": "Выберите Категорию:",
            "source_parameters": "Исходные Параметры (Выберите Несколько При Необходимости):",
            "target_parameter": "Целевой Параметр (Выберите Один):",
            "execute": "Выполнить",
            "cancel": "Отмена",
            "invalid_category": "Выбрана недопустимая категория",
            "no_elements": "Элементы не найдены",
            "select_category_error": "Пожалуйста, выберите категорию",
            "no_elements_error": "Элементы не найдены для выбранной категории",
            "select_source_error": "Пожалуйста, выберите хотя бы один исходный параметр",
            "select_target_error": "Пожалуйста, выберите целевой параметр",
            "elements_updated": "{} элементов обновлено значениями параметров из [{}] в параметр '{}'",
            "elements_failed": "{} элементов не удалось обновить.",
        },
    }

    # Default to English if language not found
    return translations.get(revit_language, translations["English"])


def get_category_mapping():
    """Create a sorted mapping of category names to built-in categories."""
    doc = HOST_APP.doc
    return {
        cat.Name: cat.BuiltInCategory
        for cat in sorted(doc.Settings.Categories, key=lambda x: x.Name)
    }


def get_elements_by_category(category_name, category_mapping, texts):
    """Get all elements of the specified category."""
    doc = HOST_APP.doc
    if category_name not in category_mapping:
        forms.alert(texts["invalid_category"], exitscript=True)
        return []

    elements = list(
        DB.FilteredElementCollector(doc)
        .OfCategory(category_mapping[category_name])
        .WhereElementIsNotElementType()
        .ToElements()
    )

    if not elements:
        forms.alert(texts["no_elements"], exitscript=True)
        return []

    return elements


def get_parameter_names(element):
    """Extract parameter names from an element."""
    return sorted(param.Definition.Name for param in element.Parameters)


def get_parameter_value(element, parameter_name):
    """Safely get parameter value as string."""
    param = element.LookupParameter(parameter_name)
    if param:
        value = param.AsValueString()
        return value if value is not None else ""
    return ""


def create_parameter_value(element, parameter_names, separator="-", space_option="beforeafter"):
    """Create combined parameter value from multiple parameters with separators and spacing options."""
    if not parameter_names:
        return ""

    values = [
        get_parameter_value(element, param_name) for param_name in parameter_names
    ]

    # Split the separator string by spaces
    separators = separator.split() if separator.strip() else ["-"]

    # Combine values with cycling separators
    combined = values[0]
    for i, val in enumerate(values[1:], start=1):
        sep = separators[(i-1) % len(separators)]  # loop through separators
        # Apply spacing based on space_option
        if space_option == "none": combined += sep + val
        elif space_option == "before": combined += " " + sep + val
        elif space_option == "after": combined += sep + " " + val
        elif space_option == "beforeafter": combined += " " + sep + " " + val
        else: combined += " " + sep + " " + val  # fallback default

    return combined


class Params2ParamWindow(forms.WPFWindow):
    def __init__(self):
        try:
            # find the path of ui.xaml
            xamlfile = script.get_bundle_file("ui.xaml")
            super(Params2ParamWindow, self).__init__(xamlfile)

            # Get localized texts
            self.texts = get_localized_texts()

            # Initialize data
            self.category_mapping = get_category_mapping()
            self.elements = []
            self.parameter_names = []

            # Set localized window title
            self.Title = self.texts["window_title"]

            # Populate category dropdown
            self.populate_categories()

            # Get UI elements
            self.categoryComboBox = self.FindName("categoryComboBox")
            self.sourceParametersListBox = self.FindName("sourceParametersListBox")
            self.targetParametersListBox = self.FindName("targetParametersListBox")
            self.separatorTextBox = self.FindName("separatorTextBox")
            
            # Set default separator
            if self.separatorTextBox:
                self.separatorTextBox.Text = "-"

            # Set localized text for UI elements
            self.set_localized_texts()

            # Set up event handlers
            self.categoryComboBox.SelectionChanged += self.category_selection_changed

        except Exception as e:
            forms.alert(
                "Error in window initialization: {}".format(str(e)), exitscript=True
            )

    def set_localized_texts(self):
        """Set localized text for UI elements."""

        # Update buttons directly by name
        execute_button = self.FindName("executeButton")
        if execute_button:
            execute_button.Content = self.texts["execute"]

        cancel_button = self.FindName("cancelButton")
        if cancel_button:
            cancel_button.Content = self.texts["cancel"]

        # Update labels by searching through the visual tree
        self._update_labels_in_tree(self)

    def _update_labels_in_tree(self, element):
        """Update labels in the visual tree."""
        try:
            # Check if this is a Label with content to update
            if hasattr(element, "Content") and element.Content is not None:
                content = str(element.Content)
                if "Select Category:" in content:
                    element.Content = self.texts["select_category"]
                elif "Source Parameters" in content:
                    element.Content = self.texts["source_parameters"]
                elif "Target Parameter" in content:
                    element.Content = self.texts["target_parameter"]

            # Get children and recurse - try multiple methods
            children = []

            # Method 1: Try Content.Children
            if hasattr(element, "Content") and element.Content is not None:
                if hasattr(element.Content, "Children"):
                    children.extend(element.Content.Children)

            # Method 2: Try direct Children property
            if hasattr(element, "Children"):
                children.extend(element.Children)

            # Method 3: Try Child property (for single child containers)
            if hasattr(element, "Child") and element.Child is not None:
                children.append(element.Child)

            # Recursively process children
            for child in children:
                if child is not None:
                    self._update_labels_in_tree(child)

        except Exception:
            # If anything fails, just continue
            pass

    def populate_categories(self):
        """Populate the category dropdown with available categories."""
        category_list = List[object]()
        # Sort category names alphabetically
        sorted_categories = sorted(self.category_mapping.items())
        for name, built_in_cat in sorted_categories:
            category_item = type(
                "CategoryItem", (), {"Name": name, "BuiltInCategory": built_in_cat}
            )()
            category_list.Add(category_item)

        self.categoryComboBox.ItemsSource = category_list

    def category_selection_changed(self, sender, args):  # noqa
        """Handle category selection change."""
        if self.categoryComboBox.SelectedItem is None:
            return

        selected_category = self.categoryComboBox.SelectedItem.Name

        # Get elements for selected category
        self.elements = get_elements_by_category(
            selected_category, self.category_mapping, self.texts
        )

        if not self.elements:
            self.sourceParametersListBox.ItemsSource = None
            self.targetParametersListBox.ItemsSource = None
            return

        # Get parameter names from all elements to ensure completeness
        all_param_names = set()
        for elem in self.elements[:min(5, len(self.elements))]:  # Sample first 5 elements
            all_param_names.update(get_parameter_names(elem))
        self.parameter_names = sorted(all_param_names)

        # Populate source parameter list (all parameters)
        source_param_list = List[str]()
        source_param_list.AddRange(self.parameter_names)
        self.sourceParametersListBox.ItemsSource = source_param_list

        # Populate target parameter list (only writable string parameters)
        target_param_names = set()
        for elem in self.elements[:min(5, len(self.elements))]:  # sample first 5 elements
            for p in elem.Parameters:
                if p.Definition and p.StorageType == DB.StorageType.String and not p.IsReadOnly:
                    target_param_names.add(p.Definition.Name)

        target_param_list = List[str]()
        target_param_list.AddRange(sorted(target_param_names))
        self.targetParametersListBox.ItemsSource = target_param_list

    def execute_button_click(self, sender, args):  # noqa
        """Handle execute button click."""
        # Validate selections
        if self.categoryComboBox.SelectedItem is None:
            forms.alert(self.texts["select_category_error"], exitscript=True)
            return

        if not self.elements:
            forms.alert(self.texts["no_elements_error"], exitscript=True)
            return

        selected_source_params = list(self.sourceParametersListBox.SelectedItems)
        if not selected_source_params:
            forms.alert(self.texts["select_source_error"], exitscript=True)
            return

        selected_target_param = self.targetParametersListBox.SelectedItem
        if not selected_target_param:
            forms.alert(self.texts["select_target_error"], exitscript=True)
            return

        # Execute the parameter copying
        self.copy_parameters(selected_source_params, selected_target_param)

        # Close the window
        self.Close()

    def copy_parameters(self, source_parameters, target_parameter):
        """Copy parameter values from source to target parameter."""
        updated_count = 0
        failed_count = 0

        with revit.Transaction("Set parameters values in target parameter"):
            for element in self.elements:
                try:
                    # Get the target parameter
                    target_param = element.LookupParameter(target_parameter)
                    if not target_param:
                        failed_count += 1
                        continue

                    # Create combined value from source parameters with user-defined separators
                    separator = "-"
                    if hasattr(self, "separatorTextBox") and self.separatorTextBox.Text.strip():
                        separator = self.separatorTextBox.Text.strip()

                    space_option = "beforeafter"  # default
                    if hasattr(self, "spaceNoneRadio") and self.spaceNoneRadio.IsChecked: space_option = "none"
                    elif hasattr(self, "spaceBeforeRadio") and self.spaceBeforeRadio.IsChecked: space_option = "before"
                    elif hasattr(self, "spaceAfterRadio") and self.spaceAfterRadio.IsChecked: space_option = "after"
                    elif hasattr(self, "spaceBeforeAfterRadio") and self.spaceBeforeAfterRadio.IsChecked: space_option = "beforeafter"
                    
                    param_value = create_parameter_value(element, source_parameters, separator, space_option)

                    # Set the value based on storage type
                    if target_param.StorageType == DB.StorageType.String:
                        target_param.Set(param_value)
                    elif target_param.StorageType == DB.StorageType.Double:
                        # Only set if single source parameter and numeric
                        if len(source_parameters) == 1:
                            try:
                                target_param.Set(float(param_value))
                            except (ValueError, TypeError):
                                failed_count += 1
                                continue
                        else:
                            failed_count += 1  # Cannot concatenate into numeric parameter
                            continue
                    else:
                        # For other types, skip
                        failed_count += 1
                        continue

                    updated_count += 1

                except (AttributeError, ArgumentException, NullReferenceException):
                    # Handle common Revit API exceptions
                    failed_count += 1
                    continue

        source_params_str = ", ".join(str(p) for p in source_parameters)
        message = self.texts["elements_updated"].format(
            updated_count, source_params_str, target_parameter
        )

        if failed_count > 0:
            message += "\n\n" + self.texts["elements_failed"].format(failed_count)

        forms.alert(message)

    def cancel_button_click(self, sender, args):  # noqa
        """Handle cancel button click."""
        self.Close()


def main():
    """Main execution function."""
    try:
        # Show the XAML window
        window = Params2ParamWindow()
        window.show_dialog()
    except Exception as e:
        forms.alert("Error initializing window: {}".format(str(e)), exitscript=True)


if __name__ == "__main__":
    main()
