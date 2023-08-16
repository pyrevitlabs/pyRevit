"""Document colorizer python API."""
#pylint: disable=import-error,invalid-name,broad-except
#pylint: disable=no-member
from pyrevit import HOST_APP
from pyrevit.runtime import types
from pyrevit.framework import Media
from pyrevit.framework import List, Regex
from pyrevit.coreutils import envvars


def hex_to_brush(color_hex):
    """Convert hex color to WPF brush."""
    return Media.SolidColorBrush(
        Media.ColorConverter.ConvertFromString(color_hex)
    )


def hex_from_brush(solid_brush):
    """Convert WPF brush to hex color."""
    color = solid_brush.Color
    color_hex = ''.join(
        '{:02X}'.format(int(x)) for x in
        [color.A, color.R, color.G, color.B]
        )
    return '#' + color_hex


def _get_tabcoloring_cfgs(usercfg):
    # read custom configs for this
    if not usercfg.has_section("tabcoloring"):
        usercfg.add_section("tabcoloring")
    return usercfg.get_section("tabcoloring")


def _get_sort_colorize_docs(tabcfgs):
    return tabcfgs.get_option('sort_colorize_docs', False)


def _set_sort_colorize_docs(tabcfgs, theme):
    tabcfgs.sort_colorize_docs = theme.SortDocTabs


def _get_tab_orderrules(tabcfgs, default=False):
    default_colors = \
        [hex_from_brush(b) for b in types.TabColoringTheme.DefaultBrushes]
    tab_colors = default_colors
    if not default:
        tab_colors = tabcfgs.get_option('tab_colors', default_colors)
    return List[types.TabColoringRule](
        [types.TabColoringRule(hex_to_brush(c)) for c in tab_colors]
        )


def _set_tab_ordercolors(tabcfgs, theme):
    tabcfgs.tab_colors = \
        [hex_from_brush(c.Brush) for c in theme.TabOrderRules]


def _get_tab_filterrules(tabcfgs):
    tab_filtercolors = tabcfgs.get_option('tab_filtercolors', {})
    return List[types.TabColoringRule](
        [types.TabColoringRule(hex_to_brush(c), f)
         for c, f in tab_filtercolors.items()]
    )


def _set_tab_filtercolors(tabcfgs, theme):
    tabcfgs.tab_filtercolors = \
        {hex_from_brush(c.Brush):str(c.TitleFilter)
         for c in theme.TabFilterRules}


def _get_tabstyle(tabcfgs):
    tabstyle_index = tabcfgs.get_option(
        'tabstyle_index',
        types.TabColoringTheme.DefaultTabColoringStyleIndex
        )
    return types.TabColoringTheme.AvailableStyles[tabstyle_index]


def _set_tabstyle(tabcfgs, theme):
    tabcfgs.tabstyle_index = \
        types.TabColoringTheme.AvailableStyles.IndexOf(theme.TabStyle)


def _get_family_tabstyle(tabcfgs):
    family_tabstyle_index = tabcfgs.get_option(
        'family_tabstyle_index',
        types.TabColoringTheme.DefaultFamilyTabColoringStyleIndex
        )
    return types.TabColoringTheme.AvailableStyles[family_tabstyle_index]


def _set_family_tabstyle(tabcfgs, theme):
    tabcfgs.family_tabstyle_index = \
        types.TabColoringTheme.AvailableStyles.IndexOf(theme.FamilyTabStyle)


def get_tabcoloring_theme(usercfg):
    """Get tab coloring theme from settings."""
    tabcfgs = _get_tabcoloring_cfgs(usercfg)

    theme = types.TabColoringTheme()
    theme.SortDocTabs = _get_sort_colorize_docs(tabcfgs)
    theme.TabStyle = _get_tabstyle(tabcfgs)
    theme.FamilyTabStyle = _get_family_tabstyle(tabcfgs)

    theme.TabOrderRules = _get_tab_orderrules(tabcfgs)
    theme.TabFilterRules = _get_tab_filterrules(tabcfgs)

    return theme


def reset_tab_ordercolors(usercfg, theme):
    """Reset tab order colors to internal default."""
    tabcfgs = _get_tabcoloring_cfgs(usercfg)
    theme.TabOrderRules = _get_tab_orderrules(tabcfgs, default=True)


def set_tabcoloring_theme(usercfg, theme):
    """Set tab coloring theme in settings."""
    tabcfgs = _get_tabcoloring_cfgs(usercfg)

    _set_sort_colorize_docs(tabcfgs, theme)
    _set_tabstyle(tabcfgs, theme)
    _set_family_tabstyle(tabcfgs, theme)

    _set_tab_ordercolors(tabcfgs, theme)
    _set_tab_filtercolors(tabcfgs, theme)


def get_tab_orderrule(theme, index):
    """Get coloring rule from active theme, at index."""
    return hex_from_brush(theme.TabOrderRules[index].Brush)


def add_tab_orderrule(theme, color):
    """Add coloring rule to active theme."""
    theme.TabOrderRules.Add(
        types.TabColoringRule(hex_to_brush(color))
        )


def remove_tab_orderrule(theme, index):
    """Remove coloring rule at index, from active theme."""
    theme.TabOrderRules.RemoveAt(index)


def update_tab_orderrule(theme, index, color):
    """Update coloring rule at index, on active theme."""
    tor = theme.TabOrderRules[index]
    tor.Brush = hex_to_brush(color)


def get_tab_filterrule(theme, index):
    """Get coloring filter rule from active theme, at index."""
    tfr = theme.TabFilterRules[index]
    color = tfr.Brush.Color
    color_hex = ''.join(
        '{:02X}'.format(int(x)) for x in
        [color.A, color.R, color.G, color.B]
        )
    return '#' + color_hex, str(tfr.TitleFilter)


def add_tab_filterrule(theme, color, title_filter):
    """Add coloring filter rule to active theme."""
    fc = types.TabColoringRule(hex_to_brush(color), title_filter)
    theme.TabFilterRules.Add(fc)


def remove_tab_filterrule(theme, index):
    """Remove coloring filter rule at index, from active theme."""
    theme.TabFilterRules.RemoveAt(index)


def update_tab_filterrule(theme, index, color=None, title_filter=None):
    """Update coloring filter rule at index, on active theme."""
    tfr = theme.TabFilterRules[index]
    if color:
        tfr.Brush = hex_to_brush(color)
    if title_filter:
        tfr.TitleFilter = Regex(title_filter)


def update_tabstyle(theme, tab_style):
    """Update current tab style."""
    for ts in types.TabColoringTheme.AvailableStyles:
        if ts.Name == tab_style.Name:
            theme.TabStyle = ts


def update_family_tabstyle(theme, tab_style):
    """Update current family tab style."""
    for ts in types.TabColoringTheme.AvailableStyles:
        if ts.Name == tab_style.Name:
            theme.FamilyTabStyle = ts


def get_doc_colorizer_state():
    """Get state of document colorizer."""
    return types.DocumentTabEventUtils.IsUpdatingDocumentTabs


def get_styled_slots():
    """Get list of current styling slots."""
    active_theme = types.DocumentTabEventUtils.TabColoringTheme
    if active_theme:
        return list(active_theme.StyledDocuments)


def toggle_doc_colorizer():
    """Toggle state of document colorizer."""
    if types.DocumentTabEventUtils.IsUpdatingDocumentTabs:
        types.DocumentTabEventUtils.StopGroupingDocumentTabs()
    else:
        types.DocumentTabEventUtils.StartGroupingDocumentTabs(HOST_APP.uiapp)
    return types.DocumentTabEventUtils.IsUpdatingDocumentTabs


def reset_doc_colorizer():
    """Reset document colorizer."""
    types.DocumentTabEventUtils.ResetGroupingDocumentTabs()


def init_doc_colorizer(usercfg):
    """Initialize document colorizer from settings."""
    uiapp = HOST_APP.uiapp
    if HOST_APP.is_newer_than(2018):
        current_tabcolorizer = \
            envvars.get_pyrevit_env_var(envvars.TABCOLORIZER_ENVVAR)

        new_theme = get_tabcoloring_theme(usercfg)

        # cancel out the colorizer from previous runtime version
        if current_tabcolorizer:
            # TODO: adopt the previous slots state
            # prev_theme = current_tabcolorizer.TabColoringTheme
            # if prev_theme:
            #     new_theme.InitSlots(prev_theme)
            current_tabcolorizer.StopGroupingDocumentTabs()

        # start or stop the document colorizer
        types.DocumentTabEventUtils.TabColoringTheme = new_theme
        if usercfg.colorize_docs:
            types.DocumentTabEventUtils.StartGroupingDocumentTabs(uiapp)
        else:
            types.DocumentTabEventUtils.StopGroupingDocumentTabs()

        # set the new colorizer
        envvars.set_pyrevit_env_var(
            envvars.TABCOLORIZER_ENVVAR,
            types.DocumentTabEventUtils
            )
