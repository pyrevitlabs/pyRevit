"""Select all element types of chosen category."""
#pylint: disable=E0401,W0703,C0103
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()


# collect all element types
element_types = \
    {x.FamilyName
     for x in revit.query.get_types_by_class(DB.ElementType, doc=revit.doc)
     if x.FamilyName}

graphic_styles = \
    {'Graphics Styles: ' + x.GraphicsStyleCategory.Name
     for x in revit.query.get_types_by_class(DB.GraphicsStyle, doc=revit.doc)
     if x.GraphicsStyleCategory
     and x.GraphicsStyleCategory.CategoryType != DB.CategoryType.Internal}

all_options = list(element_types)
all_options.extend(graphic_styles)
all_options.extend(['Fill Patterns', 'Area Schemes', 'Line Styles'])
selected_option = \
    forms.CommandSwitchWindow.show(all_options,
                                   message='Pick type category:')

if selected_option:
    selection = revit.get_selection()
    if selected_option == 'Fill Patterns':
        fill_patterns = revit.query.get_types_by_class(DB.FillPatternElement,
                                                       doc=revit.doc)
        selection.set_to(list(fill_patterns))
    elif selected_option == 'Area Schemes':
        area_schemes = revit.query.get_types_by_class(DB.AreaScheme,
                                                      doc=revit.doc)
        selection.set_to(list(area_schemes))
    elif selected_option == 'Line Styles':
        line_styles = revit.query.get_line_styles(doc=revit.doc)
        selection.set_to(list(line_styles))
    elif selected_option.startswith('Graphics Styles: '):
        graphic_style_cat = selected_option.replace('Graphics Styles: ', '')
        graphic_styles = \
            [x for x in revit.query.get_types_by_class(DB.GraphicsStyle,
                                                       doc=revit.doc)
             if x.GraphicsStyleCategory
             and x.GraphicsStyleCategory.CategoryType != DB.CategoryType.Internal
             and graphic_style_cat == x.GraphicsStyleCategory.Name]
        selection.set_to(list(graphic_styles))
    else:
        all_types = \
            revit.query.get_types_by_class(DB.ElementType, doc=revit.doc)
        selection.set_to([x for x in all_types
                          if selected_option == x.FamilyName
                          and revit.query.get_name(x) != x.FamilyName])
