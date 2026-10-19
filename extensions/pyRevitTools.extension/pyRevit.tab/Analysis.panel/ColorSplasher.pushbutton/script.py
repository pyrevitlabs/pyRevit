# -*- coding: utf-8 -*-
"""Color the elements of the active view by parameter value.

The window is modeless and single-instance: running the command again brings
the open window to the front. Revit API writes run through
``events.execute_in_revit_context``; view and document changes reach the
window through ``events.handle`` subscriptions owned by this execution.
"""

from re import split
from unicodedata import category as unicode_category
from unicodedata import normalize

from pyrevit import forms, revit, script
from pyrevit import HOST_APP
from pyrevit import DB
from pyrevit.compat import get_elementid_value_func
from pyrevit.coreutils import applocales, distinct_rgb_colors, unique_name
from pyrevit.framework import Drawing, Forms, List, Media, System, Windows, Input
from pyrevit.revit import create, events, query

logger = script.get_logger()
config = script.get_config()
get_elementid_value = get_elementid_value_func()

WINDOW_ENV_KEY = "PYREVITTOOLS_COLORSPLASHER_WINDOW"
XAML_FILE = "ColorSplasherWindow.xaml"
SCHEME_FILES_FILTER = "Color Scheme (*.cschn)|*.cschn"
NONE_VALUE = "None"
INVALID_NAME_CHARS = "{}[]:\\|?/<>*"

CAT_EXCLUDED = frozenset(
    (
        int(DB.BuiltInCategory.OST_RoomSeparationLines),
        int(DB.BuiltInCategory.OST_Cameras),
        int(DB.BuiltInCategory.OST_CurtainGrids),
        int(DB.BuiltInCategory.OST_Elev),
        int(DB.BuiltInCategory.OST_Grids),
        int(DB.BuiltInCategory.OST_IOSModelGroups),
        int(DB.BuiltInCategory.OST_Views),
        int(DB.BuiltInCategory.OST_SitePropertyLineSegment),
        int(DB.BuiltInCategory.OST_SectionBox),
        int(DB.BuiltInCategory.OST_ShaftOpening),
        int(DB.BuiltInCategory.OST_BeamAnalytical),
        int(DB.BuiltInCategory.OST_StructuralFramingOpening),
        int(DB.BuiltInCategory.OST_MEPSpaceSeparationLines),
        int(DB.BuiltInCategory.OST_DuctSystem),
        int(DB.BuiltInCategory.OST_Lines),
        int(DB.BuiltInCategory.OST_PipingSystem),
        int(DB.BuiltInCategory.OST_Matchline),
        int(DB.BuiltInCategory.OST_CenterLines),
        int(DB.BuiltInCategory.OST_CurtainGridsRoof),
        int(DB.BuiltInCategory.OST_SWallRectOpening),
        -2000278,
        -1,
    )
)
COLOR_SCHEME_CATEGORIES = frozenset(
    (
        int(DB.BuiltInCategory.OST_Rooms),
        int(DB.BuiltInCategory.OST_MEPSpaces),
        int(DB.BuiltInCategory.OST_Areas),
    )
)
EXCLUDED_PARAMETERS = (
    DB.BuiltInParameter.ELEM_CATEGORY_PARAM,
    DB.BuiltInParameter.ELEM_CATEGORY_PARAM_MT,
)
FILTERABLE_STORAGE_TYPES = (
    DB.StorageType.String,
    DB.StorageType.Integer,
    DB.StorageType.Double,
    DB.StorageType.ElementId,
)

doc = None
active_view = None
splasher_window = None


class FilterCreationError(Exception):
    """View filters cannot be built; ``message_key`` names the locale message."""

    def __init__(self, message_key):
        Exception.__init__(self, message_key)
        self.message_key = message_key


class CategoryInfo(object):
    """Category with elements in the active view and its selectable parameters."""

    def __init__(self, category, parameters):
        self.name = strip_accents(category.Name)
        self.category = category
        self.parameters = parameters

    @property
    def uses_color_scheme(self):
        return int(get_elementid_value(self.category.Id)) in COLOR_SCHEME_CATEGORIES


class ParameterInfo(object):
    """Parameter sampled from one element of a category.

    Values are looked up by definition name on every element, or on its type
    when ``is_type_parameter`` is set.
    """

    def __init__(self, parameter, is_type_parameter):
        self.name = strip_accents(parameter.Definition.Name)
        self.lookup_name = parameter.Definition.Name
        self.id = parameter.Id
        self.storage_type = parameter.StorageType
        self.is_type_parameter = is_type_parameter


class ValueInfo(object):
    """One display value of a parameter, the elements holding it, and its color.

    ``raw_values`` keeps every distinct stored value behind the display value,
    since rounding in ``AsValueString`` can merge several of them.
    """

    def __init__(self, name):
        self.name = name
        self.element_ids = List[DB.ElementId]()
        self.raw_values = []
        self.color = (0, 0, 0)
        self.background_brush = None
        self.foreground_brush = None

    @property
    def is_none(self):
        return self.name == NONE_VALUE

    def add(self, element_id, raw_value):
        self.element_ids.Add(element_id)
        if raw_value not in self.raw_values:
            self.raw_values.append(raw_value)

    def set_color(self, red, green, blue):
        self.color = (red, green, blue)
        self.background_brush = Media.SolidColorBrush(
            Media.Color.FromRgb(red, green, blue)
        )
        is_light = (red * 299 + green * 587 + blue * 114) / 1000.0 > 128
        self.foreground_brush = Media.Brushes.Black if is_light else Media.Brushes.White


class OverrideOptions(object):
    """Graphic override channels that receive the value colors.

    Invariant:
        At least one channel is enabled; with none checked in the UI the
        foreground pattern is used.
    """

    def __init__(self, line, foreground, background):
        self.line = line
        self.foreground = foreground or not (line or background)
        self.background = background

    def for_legend(self):
        """Return options for legend swatches, which only have a foreground pattern."""
        return OverrideOptions(self.line, self.foreground or self.background, False)


def update_context():
    """Refresh the module-wide ``doc`` and ``active_view`` every action reads."""
    global doc, active_view
    doc = revit.doc
    active_view = get_colorable_view(doc)


def get_colorable_view(document):
    """Return the view whose graphics Color Splasher overrides, or None.

    When the project or system browser has focus, the first open UI view
    stands in for it. Views that cannot take temporary visibility modes are
    rejected because they do not support element overrides.
    """
    if document is None or document.ActiveView is None:
        return None
    view = document.ActiveView
    if view.ViewType in (DB.ViewType.ProjectBrowser, DB.ViewType.SystemBrowser):
        view = document.GetElement(revit.uidoc.GetOpenUIViews()[0].ViewId)
    if not view.CanUseTemporaryVisibilityModes():
        return None
    return view


def refresh_window(sender, args):
    """Reload the window's categories for the newly active view or document."""
    try:
        update_context()
        if splasher_window:
            splasher_window.Dispatcher.Invoke(
                System.Action(splasher_window.reload_categories)
            )
    except Exception:
        logger.exception("Could not refresh Color Splasher for the active view.")


def strip_accents(text):
    return "".join(
        char for char in normalize("NFKD", text) if unicode_category(char) != "Mn"
    )


def sanitize_name(text):
    """Remove characters Revit rejects in view and filter names."""
    return "".join(char for char in text if char not in INVALID_NAME_CHARS)


def get_filter_name(category, parameter, value_name):
    """Return the view filter name for a value; with an empty value, the shared prefix."""
    return sanitize_name("{} {} - {}".format(category.name, parameter.name, value_name))


def get_used_categories(view):
    """Return the model categories with view-independent elements in the view."""
    collector = (
        DB.FilteredElementCollector(doc, view.Id)
        .WhereElementIsNotElementType()
        .WhereElementIsViewIndependent()
    )
    categories = {}
    for element in collector:
        category = element.Category
        if category is None:
            continue
        category_id = int(get_elementid_value(category.Id))
        if (
            category_id >= -1
            or category_id in CAT_EXCLUDED
            or category_id in categories
        ):
            continue
        categories[category_id] = CategoryInfo(category, get_parameters(element))
    return sorted(categories.values(), key=lambda info: info.name)


def get_parameters(element):
    """Return the instance and type parameters of a sample element, sorted by name."""
    parameters = [
        ParameterInfo(parameter, False)
        for parameter in element.Parameters
        if parameter.Definition.BuiltInParameter not in EXCLUDED_PARAMETERS
    ]
    element_type = query.get_type(element)
    if element_type:
        parameters.extend(
            ParameterInfo(parameter, True)
            for parameter in element_type.Parameters
            if parameter.Definition.BuiltInParameter not in EXCLUDED_PARAMETERS
        )
    return sorted(parameters, key=lambda info: info.name.upper())


def collect_values(view, category, parameter):
    """Group the category's elements in the view by the parameter's display value.

    Returns:
        list[ValueInfo]: without colors; ordered by ``sort_values``.
    """
    values = {}
    elements = query.get_elements_by_categories(
        [category.category], doc=doc, view_id=view.Id
    )
    for element in elements:
        source = query.get_type(element) if parameter.is_type_parameter else element
        revit_parameter = query.get_param(source, parameter.lookup_name)
        if revit_parameter is None:
            continue
        display_value = (
            revit_parameter.AsValueString() if revit_parameter.HasValue else NONE_VALUE
        )
        if display_value not in values:
            values[display_value] = ValueInfo(display_value)
        values[display_value].add(element.Id, query.get_param_value(revit_parameter))
    return sort_values(list(values.values()))


def sort_values(values):
    """Sort values alphabetically, or numerically when they end in a unit suffix.

    The suffix length is taken from the first value; values that do not parse
    as numbers go last, followed by the None value.
    """
    named = sorted(
        (value for value in values if not value.is_none), key=lambda value: value.name
    )
    if named:
        first_name = named[0].name
        suffix_length = _count_trailing_non_digits(first_name)
        if suffix_length == 0:
            named.sort(key=lambda value: _to_float(value.name))
        elif 0 < suffix_length < len(first_name):
            named.sort(key=lambda value: _to_float(value.name[:-suffix_length]))
    return named + [value for value in values if value.is_none]


def _count_trailing_non_digits(text):
    for index, char in enumerate(reversed(text)):
        if char.isdigit():
            return index
    return -1


def _to_float(text):
    try:
        return float(text)
    except ValueError:
        return float("inf")


def assign_distinct_colors(values):
    for value, color in zip(values, distinct_rgb_colors(len(values))):
        value.set_color(*color)


def interpolate_color(start, end, ratio):
    return tuple(int(round(s + (e - s) * ratio)) for s, e in zip(start, end))


def faded_color(color):
    """Return a lighter, desaturated shade used for lines next to pattern fills."""
    tinted = [int(channel + (255 - channel) * 0.6) for channel in color]
    gray = sum(tinted) / 3.0
    return DB.Color(*[int(channel * 0.7 + gray * 0.3) for channel in tinted])


def build_overrides(color, options, solid_fill_id):
    base_color = DB.Color(*color)
    overrides = DB.OverrideGraphicSettings()
    if options.line:
        if options.foreground or options.background:
            line_color = faded_color(color)
        else:
            line_color = base_color
        overrides.SetProjectionLineColor(line_color)
        overrides.SetCutLineColor(line_color)
    if options.foreground:
        overrides.SetSurfaceForegroundPatternColor(base_color)
        overrides.SetCutForegroundPatternColor(base_color)
        if solid_fill_id is not None:
            overrides.SetSurfaceForegroundPatternId(solid_fill_id)
            overrides.SetCutForegroundPatternId(solid_fill_id)
    if options.background:
        overrides.SetSurfaceBackgroundPatternColor(base_color)
        overrides.SetCutBackgroundPatternColor(base_color)
        if solid_fill_id is not None:
            overrides.SetSurfaceBackgroundPatternId(solid_fill_id)
            overrides.SetCutBackgroundPatternId(solid_fill_id)
    return overrides


def get_solid_fill_id():
    solid_fill = query.get_solid_fillpattern_element(doc)
    return solid_fill.Id if solid_fill else None


def ensure_color_fill_scheme(category):
    """Give the view the category's first non-empty color scheme if it has none.

    Rooms, spaces and areas may not show element overrides without one.
    """
    category_id = category.category.Id
    if active_view.GetColorFillSchemeId(category_id) != DB.ElementId.InvalidElementId:
        return
    for scheme in query.get_elements_by_class(DB.ColorFillScheme, doc=doc):
        if scheme.CategoryId == category_id and len(scheme.GetEntries()) > 0:
            active_view.SetColorFillSchemeId(category_id, scheme.Id)
            return


def apply_colors(category, parameter, colors, options):
    """Override element graphics in the active view with their value's color.

    Values are collected again so elements added since the list was built
    are colored too; ``colors`` maps display values to RGB tuples.

    Note:
        Must run in Revit API context.
    """
    solid_fill_id = get_solid_fill_id()
    with revit.Transaction("Apply colors to elements", doc=doc):
        if category.uses_color_scheme and HOST_APP.is_newer_than(2021):
            ensure_color_fill_scheme(category)
        for value in collect_values(active_view, category, parameter):
            color = colors.get(value.name)
            if color is None:
                continue
            overrides = build_overrides(color, options, solid_fill_id)
            for element_id in value.element_ids:
                active_view.SetElementOverrides(element_id, overrides)


def reset_colors(filter_prefix):
    """Clear element overrides in the active view and drop its matching filters.

    Filters whose name starts with ``filter_prefix`` are removed from the view
    only; the filter elements stay in the document for reuse.

    Note:
        Must run in Revit API context.
    """
    with revit.Transaction("Reset colors in elements", doc=doc):
        if filter_prefix:
            for view_filter in query.get_view_filters(active_view):
                if view_filter.Name.startswith(filter_prefix):
                    active_view.RemoveFilter(view_filter.Id)
        overrides = DB.OverrideGraphicSettings()
        element_ids = (
            DB.FilteredElementCollector(doc, active_view.Id)
            .WhereElementIsNotElementType()
            .WhereElementIsViewIndependent()
            .ToElementIds()
        )
        for element_id in element_ids:
            active_view.SetElementOverrides(element_id, overrides)


def get_filter_rule_values(storage_type, value):
    """Return the stored values a filter must match for a display value.

    An empty list means no rule can express the value, which happens for
    unset double parameters.
    """
    if not value.is_none:
        return value.raw_values
    if storage_type == DB.StorageType.String:
        return [""]
    if storage_type == DB.StorageType.Integer:
        return [0]
    if storage_type == DB.StorageType.ElementId:
        return [DB.ElementId.InvalidElementId]
    return []


def create_filters(category, parameter, values, options):
    """Add one view filter per value to the active view, colored like the value.

    Filters with the same name from earlier runs are reused instead of
    recreated. All filters are created in one transaction.

    Raises:
        FilterCreationError: the parameter cannot drive a filter rule.

    Note:
        Must run in Revit API context.
    """
    if parameter.storage_type not in FILTERABLE_STORAGE_TYPES:
        raise FilterCreationError("ColorSplasher.Messages.FilterNotSupported")
    category_ids = List[DB.ElementId]([category.category.Id])
    filterable_ids = DB.ParameterFilterUtilities.GetFilterableParametersInCommon(
        doc, category_ids
    )
    if not filterable_ids.Contains(parameter.id):
        raise FilterCreationError("ColorSplasher.Messages.FilterCreationFailed")

    builtin_category = query.get_builtincategory(category.category, doc=doc)
    existing_filters = {
        view_filter.Name: view_filter for view_filter in query.get_rule_filters(doc)
    }
    solid_fill_id = get_solid_fill_id()
    with revit.Transaction("Create View Filters", doc=doc, log_errors=False):
        for value in values:
            filter_name = get_filter_name(category, parameter, value.name)
            view_filter = existing_filters.get(filter_name)
            if view_filter is None:
                rule_values = get_filter_rule_values(parameter.storage_type, value)
                if not rule_values:
                    logger.debug("No filter rule for value '%s'.", value.name)
                    continue
                view_filter = create.create_param_value_filter(
                    filter_name,
                    parameter.id,
                    rule_values,
                    "==",
                    match_any=True,
                    category_list=[builtin_category],
                    doc=doc,
                )
            if not active_view.IsFilterApplied(view_filter.Id):
                active_view.AddFilter(view_filter.Id)
            active_view.SetFilterOverrides(
                view_filter.Id, build_overrides(value.color, options, solid_fill_id)
            )


def get_text_note_type_id():
    type_id = doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType)
    if type_id != DB.ElementId.InvalidElementId:
        return type_id
    text_types = query.get_types_by_class(DB.TextNoteType, doc=doc)
    if not text_types:
        raise Exception("No text note type found in the model")
    return text_types[0].Id


def get_solid_filled_region_type():
    """Return a filled region type with a solid foreground, creating one if needed.

    Note:
        Must run inside a transaction.
    """
    region_types = query.get_types_by_class(DB.FilledRegionType, doc=doc)
    for region_type in region_types:
        pattern = doc.GetElement(region_type.ForegroundPatternId)
        if (
            pattern is not None
            and pattern.GetFillPattern().IsSolidFill
            and region_type.ForegroundPatternColor.IsValid
        ):
            return region_type
    solid_fill = query.get_solid_fillpattern_element(doc)
    if not region_types or solid_fill is None:
        raise Exception("Could not find or create a solid fill region type")
    taken_names = {query.get_name(region_type) for region_type in region_types}
    new_type = region_types[0].Duplicate(unique_name("Solid Fill", taken_names))
    new_type.ForegroundPatternId = solid_fill.Id
    return new_type


def rectangle_loops(x, y, width, height):
    corners = [
        DB.XYZ(x, y, 0),
        DB.XYZ(x, y + height, 0),
        DB.XYZ(x + width, y + height, 0),
        DB.XYZ(x + width, y, 0),
    ]
    loop = DB.CurveLoop()
    for start, end in zip(corners, corners[1:] + corners[:1]):
        loop.Append(DB.Line.CreateBound(start, end))
    loops = List[DB.CurveLoop]()
    loops.Add(loop)
    return loops


def create_legend(template_legend, legend_name, label_prefix, values, options):
    """Duplicate a legend view and draw one label and color swatch per value.

    Returns:
        DB.View: the new legend, named after ``legend_name`` made unique.

    Note:
        Must run in Revit API context.
    """
    text_type_id = get_text_note_type_id()
    solid_fill_id = get_solid_fill_id()
    taken_names = {
        query.get_name(view)
        for view in query.get_all_views(doc, include_nongraphical=True)
    }
    with revit.Transaction("Create Legend", doc=doc, log_errors=False):
        region_type = get_solid_filled_region_type()
        legend = doc.GetElement(
            template_legend.Duplicate(DB.ViewDuplicateOption.Duplicate)
        )
        legend.Name = unique_name(sanitize_name(legend_name), taken_names)

        rows = []
        y_position = 0.0
        for value in values:
            text_note = DB.TextNote.Create(
                doc,
                legend.Id,
                DB.XYZ(0, y_position, 0),
                label_prefix + value.name,
                text_type_id,
            )
            doc.Regenerate()
            box = text_note.get_BoundingBox(legend)
            height = box.Max.Y - box.Min.Y
            rows.append((value, box.Min.Y, box.Max.X, height))
            y_position = box.Min.Y - height * 1.25

        spacing = rows[-1][3] * 0.25
        swatch_x = max(row[2] for row in rows) + spacing
        for value, bottom, _, height in rows:
            region = DB.FilledRegion.Create(
                doc,
                region_type.Id,
                legend.Id,
                rectangle_loops(swatch_x, bottom, height * 2, height),
            )
            legend.SetElementOverrides(
                region.Id, build_overrides(value.color, options, solid_fill_id)
            )
    return legend


def select_elements(element_ids):
    revit.get_selection().set_to(element_ids)


def parse_scheme_line(line):
    """Parse a ``<value>::R<r>G<g>B<b>`` line of a .cschn color scheme file."""
    name, rgb = line.strip().rsplit("::R", 1)
    red, green, blue = (int(channel) for channel in split(r"[GB]", rgb))
    return name, (red, green, blue)


class ColorSplasherWindow(forms.WPFWindow):
    """Modeless Color Splasher window; at most one is open per Revit session.

    Invariant:
        UI handlers only gather state. Revit API writes happen in callbacks
        scheduled through ``events.execute_in_revit_context``.
    """

    resolve_theme = True

    def __init__(self):
        forms.WPFWindow.__init__(self, XAML_FILE)
        self._values = []
        self._chk_line_color.IsChecked = config.get_option("apply_line_color", False)
        self._chk_foreground_pattern.IsChecked = config.get_option(
            "apply_foreground_pattern_color", True
        )
        self._chk_background_pattern.IsChecked = config.get_option(
            "apply_background_pattern_color", False
        )
        self.Closed += self.window_closed
        script.restore_window_position(self)
        self.reload_categories()

    @property
    def selected_category(self):
        return self._categories.SelectedItem

    @property
    def selected_parameter(self):
        return self._parameters.SelectedItem

    def reload_categories(self):
        """Repopulate categories from the active view, clearing the selection."""
        self._categories.ItemsSource = (
            get_used_categories(active_view) if active_view else []
        )
        self._categories.SelectedIndex = -1
        self.category_changed(None, None)
        self.update_window_title()

    def update_window_title(self):
        title = self.get_locale_string("ColorSplasher.Title")
        if active_view is not None:
            title = "{} | {}".format(title, query.get_name(active_view))
        self.Title = title

    def show_message(self, message, title=None):
        """Show a task dialog above this topmost window."""
        self.Topmost = False
        try:
            forms.alert(
                message,
                title=title or self.get_locale_string("ColorSplasher.TaskDialog.Title"),
            )
        finally:
            self.Topmost = True

    def alert(self, message_key, args=(), title_key=None):
        """Show the localized message ``message_key`` formatted with ``args``."""
        title = self.get_locale_string(title_key) if title_key else None
        self.show_message(self.get_locale_string(message_key).format(*args), title)

    def _set_visible(self, element, visible):
        if visible:
            self.show_element(element)
        else:
            self.hide_element(element)

    def _set_values(self, values):
        self._values = values
        self._values_list.ItemsSource = values
        self._set_visible(self._txt_placeholder_values, not values)

    def _refresh_value_colors(self):
        self._values_list.Items.Refresh()

    def _override_options(self):
        return OverrideOptions(
            bool(self._chk_line_color.IsChecked),
            bool(self._chk_foreground_pattern.IsChecked),
            bool(self._chk_background_pattern.IsChecked),
        )

    def _ensure_colorable_view(self):
        if active_view is not None:
            return True
        view = revit.active_view
        self.alert(
            "ColorSplasher.Messages.ViewTypeNotSupported",
            [view.ViewType if view else ""],
        )
        return False

    def _apply_parameter_filter(self):
        search_text = self._search_box.Text.lower()
        self._set_visible(self._txt_search_prompt, not search_text)
        if search_text:
            self._parameters.Items.Filter = System.Predicate[System.Object](
                lambda parameter: search_text in parameter.name.lower()
            )
        else:
            self._parameters.Items.Filter = None

    def category_changed(self, sender, args):
        category = self.selected_category
        self._set_visible(self._txt_category_prompt, category is None)
        self._parameters.ItemsSource = category.parameters if category else []
        self._search_box.Text = ""
        self._apply_parameter_filter()
        self.parameter_changed(None, None)

    def search_text_changed(self, sender, args):
        self._apply_parameter_filter()

    def parameter_changed(self, sender, args):
        category = self.selected_category
        parameter = self.selected_parameter
        self._set_visible(self._txt_parameter_prompt, parameter is None)
        if category is None or parameter is None or active_view is None:
            self._set_values([])
            return
        values = collect_values(active_view, category, parameter)
        assign_distinct_colors(values)
        self._set_values(values)

    def value_clicked(self, sender, args):
        """Pick a color for the clicked value, or select its elements on Shift+Click."""
        value = self._values_list.SelectedItem
        if value is None:
            return
        self._values_list.SelectedIndex = -1
        if (
            Input.Keyboard.Modifiers & Input.ModifierKeys.Shift
        ) == Input.ModifierKeys.Shift:
            events.execute_in_revit_context(select_elements, value.element_ids)
            return
        color_dialog = Forms.ColorDialog()
        color_dialog.AllowFullOpen = True
        color_dialog.Color = Drawing.Color.FromArgb(*value.color)
        if color_dialog.ShowDialog() == Forms.DialogResult.OK:
            picked = color_dialog.Color
            value.set_color(int(picked.R), int(picked.G), int(picked.B))
            self._refresh_value_colors()

    def button_click_random_colors(self, sender, args):
        assign_distinct_colors(self._values)
        self._refresh_value_colors()

    def button_click_gradient_colors(self, sender, args):
        """Recolor all values on a gradient between the first and last color."""
        if len(self._values) < 3:
            return
        start = self._values[0].color
        end = self._values[-1].color
        last_index = float(len(self._values) - 1)
        for index, value in enumerate(self._values):
            value.set_color(*interpolate_color(start, end, index / last_index))
        self._refresh_value_colors()

    def button_click_set_colors(self, sender, args):
        if not self._values or not self._ensure_colorable_view():
            return
        category = self.selected_category
        self._set_visible(
            self._txt_color_scheme_hint,
            category.uses_color_scheme and not HOST_APP.is_newer_than(2021),
        )
        events.execute_in_revit_context(
            apply_colors,
            category,
            self.selected_parameter,
            dict((value.name, value.color) for value in self._values),
            self._override_options(),
        )

    def button_click_reset(self, sender, args):
        if not self._ensure_colorable_view():
            return
        category = self.selected_category
        if category is None:
            self.alert("ColorSplasher.Messages.NoCategorySelected")
            return
        parameter = self.selected_parameter
        filter_prefix = get_filter_name(category, parameter, "") if parameter else None
        events.execute_in_revit_context(reset_colors, filter_prefix)

    def button_click_create_legend(self, sender, args):
        if not self._values:
            return
        category = self.selected_category
        parameter = self.selected_parameter
        legend_name = "{}{} - {}".format(
            self.get_locale_string("ColorSplasher.LegendNamePrefix"),
            category.name,
            parameter.name,
        )
        label_prefix = "{} / {} - ".format(category.name, parameter.name)
        events.execute_in_revit_context(
            self._create_legend,
            legend_name,
            label_prefix,
            list(self._values),
            self._override_options().for_legend(),
        )

    def _create_legend(self, legend_name, label_prefix, values, options):
        legends = query.get_all_views(doc, view_types=[DB.ViewType.Legend])
        if not legends:
            self.alert("ColorSplasher.Messages.NoLegendView")
            return
        try:
            legend = create_legend(
                legends[0], legend_name, label_prefix, values, options
            )
        except Exception as ex:
            logger.debug("Legend creation failed.", exc_info=True)
            self.alert("ColorSplasher.Messages.LegendFailed", [ex])
            return
        self.alert("ColorSplasher.Messages.LegendCreated", [legend.Name])

    def button_click_create_view_filters(self, sender, args):
        if not self._values or not self._ensure_colorable_view():
            return
        category = self.selected_category
        parameter = self.selected_parameter
        events.execute_in_revit_context(
            reset_colors, get_filter_name(category, parameter, "")
        )
        events.execute_in_revit_context(
            self._create_filters,
            category,
            parameter,
            list(self._values),
            self._override_options(),
        )

    def _create_filters(self, category, parameter, values, options):
        try:
            create_filters(category, parameter, values, options)
        except FilterCreationError as ex:
            self.alert(ex.message_key)
        except Exception:
            logger.debug("View filter creation failed.", exc_info=True)
            self.alert("ColorSplasher.Messages.FilterCreationFailed")

    def save_load_color_scheme(self, sender, args):
        if not self._values:
            self.alert(
                "ColorSplasher.SaveLoadDialog.NoValuesDetected.Message",
                title_key="ColorSplasher.SaveLoadDialog.NoValuesDetected",
            )
            return
        FormSaveLoadScheme(self).Show()

    def save_scheme(self, path):
        with open(path, "w") as scheme_file:
            for value in self._values:
                scheme_file.write("{}::R{}G{}B{}\n".format(value.name, *value.color))

    def load_scheme(self, path, by_value):
        """Recolor values from a scheme file, matched by value name or by position."""
        with open(path, "r") as scheme_file:
            entries = [parse_scheme_line(line) for line in scheme_file if line.strip()]
        if by_value:
            colors = dict(entries)
            for value in self._values:
                if value.name in colors:
                    value.set_color(*colors[value.name])
        else:
            for value, (_, color) in zip(self._values, entries):
                value.set_color(*color)
        self._refresh_value_colors()

    def window_closed(self, sender, args):
        global splasher_window
        try:
            events.stop_events()
            config.set_option("apply_line_color", self._chk_line_color.IsChecked)
            config.set_option(
                "apply_foreground_pattern_color", self._chk_foreground_pattern.IsChecked
            )
            config.set_option(
                "apply_background_pattern_color", self._chk_background_pattern.IsChecked
            )
            script.save_config()
            script.save_window_position(self)
        except Exception:
            logger.exception("Error while closing Color Splasher.")
        finally:
            splasher_window = None
            script.set_envvar(WINDOW_ENV_KEY, None)


class FormSaveLoadScheme(Forms.Form):
    """Dialog to save the window's colors to, or load them from, a .cschn file."""

    def __init__(self, splasher):
        self._splasher = splasher
        self.Font = Drawing.Font(
            self.Font.FontFamily,
            9,
            Drawing.FontStyle.Regular,
            Drawing.GraphicsUnit.Pixel,
        )
        self.TopMost = True
        self.InitializeComponent()

    def _text(self, key):
        return self._splasher.get_locale_string("ColorSplasher.SaveLoadDialog." + key)

    def InitializeComponent(self):
        tooltip = Forms.ToolTip()
        anchor_top_left = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        anchor_bottom_right = Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Right

        separator = Forms.Label()
        separator.Anchor = anchor_top_left | Forms.AnchorStyles.Right
        separator.Location = Drawing.Point(0, 0)
        separator.Size = Drawing.Size(500, 2)
        separator.BackColor = Drawing.Color.FromArgb(82, 53, 239)

        if_loading = Forms.Label()
        if_loading.Anchor = anchor_top_left
        if_loading.Location = Drawing.Point(12, 10)
        if_loading.Size = Drawing.Size(239, 23)
        if_loading.Text = self._text("IfLoading")
        tooltip.SetToolTip(if_loading, self._text("IfLoading.Tooltip"))

        self._radio_by_value = Forms.RadioButton()
        self._radio_by_value.Anchor = anchor_top_left
        self._radio_by_value.Location = Drawing.Point(19, 35)
        self._radio_by_value.Size = Drawing.Size(230, 25)
        self._radio_by_value.Text = self._text("LoadByValue")
        self._radio_by_value.Checked = True
        tooltip.SetToolTip(self._radio_by_value, self._text("LoadByValue.Tooltip"))

        radio_by_position = Forms.RadioButton()
        radio_by_position.Anchor = anchor_top_left
        radio_by_position.Location = Drawing.Point(250, 35)
        radio_by_position.Size = Drawing.Size(239, 25)
        radio_by_position.Text = self._text("LoadByPosition")
        tooltip.SetToolTip(radio_by_position, self._text("LoadByPosition.Tooltip"))

        button_save = Forms.Button()
        button_save.Anchor = anchor_bottom_right
        button_save.Location = Drawing.Point(13, 70)
        button_save.Size = Drawing.Size(236, 25)
        button_save.Text = self._text("SaveButton")
        button_save.Cursor = Forms.Cursors.Hand
        button_save.Click += self.specify_path_save

        button_load = Forms.Button()
        button_load.Anchor = anchor_bottom_right
        button_load.Location = Drawing.Point(253, 70)
        button_load.Size = Drawing.Size(236, 25)
        button_load.Text = self._text("LoadButton")
        button_load.Cursor = Forms.Cursors.Hand
        button_load.Click += self.specify_path_load

        self.SuspendLayout()
        for control in (
            if_loading,
            self._radio_by_value,
            radio_by_position,
            button_save,
            button_load,
            separator,
        ):
            self.Controls.Add(control)
        self.MaximizeBox = False
        self.MinimizeBox = False
        self.ClientSize = Drawing.Size(500, 105)
        self.Text = self._text("Title")
        self.FormBorderStyle = Forms.FormBorderStyle.FixedSingle
        self.Icon = Drawing.Icon(script.get_bundle_file("color_splasher.ico"))
        self.CenterToScreen()
        self.ResumeLayout(False)

    def _desktop(self):
        return System.Environment.GetFolderPath(
            System.Environment.SpecialFolder.Desktop
        )

    def specify_path_save(self, sender, args):
        path = forms.save_file(
            files_filter=SCHEME_FILES_FILTER,
            init_dir=self._desktop(),
            default_name="Color Scheme.cschn",
            title=self._text("SaveTitle"),
        )
        if not path:
            return
        try:
            self._splasher.save_scheme(path)
        except Exception as ex:
            logger.debug("Saving color scheme failed.", exc_info=True)
            self._splasher.show_message(str(ex), self._text("ErrorSaving"))
        self.Close()

    def specify_path_load(self, sender, args):
        path = forms.pick_file(
            files_filter=SCHEME_FILES_FILTER,
            init_dir=self._desktop(),
            title=self._text("LoadTitle"),
        )
        if not path:
            return
        try:
            self._splasher.load_scheme(path, self._radio_by_value.Checked)
        except Exception as ex:
            logger.debug("Loading color scheme failed.", exc_info=True)
            self._splasher.show_message(str(ex), self._text("ErrorLoading"))
        self.Close()


def activate_open_window():
    """Bring a window left open by an earlier run to the front.

    Returns:
        bool: True when an open window was found; stale references are cleared.
    """
    window = script.get_envvar(WINDOW_ENV_KEY)
    if window is None:
        return False
    try:
        is_open = window.IsLoaded
    except Exception:
        is_open = False
    if not is_open:
        script.set_envvar(WINDOW_ENV_KEY, None)
        return False
    if window.WindowState == Windows.WindowState.Minimized:
        window.WindowState = Windows.WindowState.Normal
    window.Activate()
    return True


def launch_color_splasher():
    global splasher_window
    xaml_path = script.get_bundle_file(XAML_FILE)

    def _t(key):
        return applocales.get_locale_string_from_xaml(xaml_path, key)

    update_context()
    if doc is None:
        forms.alert(
            _t("ColorSplasher.Messages.UnableToAccessDocument"),
            sub_msg=_t("ColorSplasher.Messages.UnableToAccessDocument.Content"),
            title=_t("ColorSplasher.TaskDialog.Error"),
            exitscript=True,
        )
    if active_view is None:
        forms.alert(
            _t("ColorSplasher.Messages.ViewTypeNotSupported").format(
                getattr(revit.active_view, "ViewType", "")
            ),
            title=_t("ColorSplasher.TaskDialog.Title"),
            exitscript=True,
        )

    splasher_window = ColorSplasherWindow()
    script.set_envvar(WINDOW_ENV_KEY, splasher_window)
    events.handle("view-activated", "doc-closed")(refresh_window)
    splasher_window.show()


if __name__ == "__main__":
    if not activate_open_window():
        launch_color_splasher()
