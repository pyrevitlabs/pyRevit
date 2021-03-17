#pylint: disable=import-error,invalid-name,broad-except
#pylint: disable=no-member
from pyrevit import HOST_APP
from pyrevit.runtime import types
from pyrevit.framework import Media
from pyrevit.framework import List, Regex
from pyrevit.coreutils import envvars


def _str_to_brush(color_hex):
    return Media.SolidColorBrush(
        Media.ColorConverter.ConvertFromString(color_hex)
    )

def _str_from_brush(solid_brush):
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


def _get_tab_ordercolors(tabcfgs):
    tab_colors = tabcfgs.get_option(
            'tab_colors',
            list(types.TabColoringTheme.DefaultBrushes)
            )
    return List[types.TabColoringColor](
        [types.TabColoringColor(x) for x in tab_colors]
        )


def _get_tab_filtercolors(tabcfgs):
    tab_filtercolors = tabcfgs.get_option('tab_filtercolors', {})
    return List[types.TabColoringColor](
        [types.TabColoringColor(x, f) for x, f in tab_filtercolors.items()]
    )


def _get_use_family_colorize_theme(tabcfgs):
    return tabcfgs.get_option('use_family_colorize_theme', False)


def _get_family_ordercolors(tabcfgs):
    family_colors = tabcfgs.get_option('family_colors', [])
    return List[types.TabColoringColor](
        [types.TabColoringColor(x) for x in family_colors]
    )


def _get_family_filtercolors(tabcfgs):
    fam_filtercolors = tabcfgs.get_option('family_filtercolors', {})
    return List[types.TabColoringColor](
        [types.TabColoringColor(x, f) for x, f in fam_filtercolors.items()]
    )


def _get_tabstyle(tabcfgs):
    tabstyle_index = tabcfgs.get_option(
        'tabstyle_index',
        types.TabColoringTheme.DefaultTabColoringStyleIndex
        )
    return types.TabColoringTheme.AvailableStyles[tabstyle_index]


def _get_family_tabstyle(tabcfgs):
    family_tabstyle_index = tabcfgs.get_option(
        'family_tabstyle_index',
        types.TabColoringTheme.DefaultFamilyTabColoringStyleIndex
        )
    return types.TabColoringTheme.AvailableStyles[family_tabstyle_index]


def get_tabcoloring_theme(usercfg):
    tabcfgs = _get_tabcoloring_cfgs(usercfg)

    theme = types.TabColoringTheme()
    theme.SortDocTabs = _get_sort_colorize_docs(tabcfgs)
    theme.TabStyle = _get_tabstyle(tabcfgs)
    theme.FamilyTabStyle = _get_family_tabstyle(tabcfgs)

    theme.TabOrderColors = _get_tab_ordercolors(tabcfgs)
    theme.TabFilterColors = _get_tab_filtercolors(tabcfgs)

    theme.UseFamilyTheme = _get_use_family_colorize_theme(tabcfgs)
    theme.FamilyTabOrderColors = _get_family_ordercolors(tabcfgs)
    theme.FamilyTabFilterColors = _get_family_filtercolors(tabcfgs)
    return theme


def get_tab_ordercolor(theme, index):
    return _str_from_brush(theme.TabOrderColors[index].Brush)


def add_tab_ordercolor(theme, color):
    theme.TabOrderColors.Add(types.TabColoringColor(color))


def remove_tab_ordercolor(theme, index):
    theme.TabOrderColors.RemoveAt(index)


def update_tab_ordercolor(theme, index, color):
    tc = theme.TabOrderColors[index]
    tc.Brush = _str_to_brush(color)


def get_tab_filtercolor(theme, index):
    tc = theme.TabOrderColors[index]
    color = tc.Color
    color_hex = ''.join(
        '{:02X}'.format(int(x)) for x in
        [color.A, color.R, color.G, color.B]
        )
    return '#' + color_hex, str(tc.TitleFilter)


def add_tab_filtercolor(theme, color, title_filter, filter_prefix=None):
    fc = theme.TabFilterColors.Add(types.TabColoringColor(color, title_filter))
    if isinstance(filter_prefix, str):
        fc.SetDefaultFilter(filter_prefix)


def remove_tab_filtercolor(theme, index):
    theme.TabFilterColors.RemoveAt(index)


def update_tab_filtercolor(theme, index, color=None, title_filter=None):
    tc = theme.TabFilterColors[index]
    if color:
        tc.Brush = _str_to_brush(color)
    if title_filter:
        tc.TitleFilter = Regex(title_filter)




def add_family_ordercolor(theme, color):
    pass

def add_family_filtercolor(theme, color):
    pass

def remove_family_ordercolor(theme, color):
    pass

def remove_family_filtercolor(theme, color):
    pass


def toggle_doc_colorizer(usercfg, theme=None):
    uiapp = HOST_APP.uiapp
    theme = theme or get_tabcoloring_theme(usercfg)

    if HOST_APP.is_newer_than(2018):
        # cancel out the colorizer from previous runtime version
        current_tabcolorizer = \
            envvars.get_pyrevit_env_var(envvars.TABCOLORIZER_ENVVAR)
        if current_tabcolorizer:
            current_tabcolorizer.StopGroupingDocumentTabs()

        # start or stop the document colorizer
        if usercfg.colorize_docs:
            types.DocumentTabEventUtils.StartGroupingDocumentTabs(uiapp)
        else:
            types.DocumentTabEventUtils.StopGroupingDocumentTabs()

        # set the new colorizer
        envvars.set_pyrevit_env_var(
            envvars.TABCOLORIZER_ENVVAR,
            types.DocumentTabEventUtils
            )
