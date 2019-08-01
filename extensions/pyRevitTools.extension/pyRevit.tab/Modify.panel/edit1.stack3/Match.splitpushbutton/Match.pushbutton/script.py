#pylint: disable=E0401,C0111,W0613,C0103
from pyrevit import HOST_APP
from pyrevit import revit, DB
from pyrevit import script
from pyrevit import forms


__helpurl__ = "{{docpath}}SrjyyGvarhw"

__doc__ = 'Pick the source object that has the element graphics override '\
          'you like to match to, and then pick the destination objects '\
          'one by one and this tool will match the graphics overrides.'\
          '\n\nShift-Click:\nShows Match Config window.'


my_config = script.get_config()


def setup_dim_overrides_per_config(from_dim, to_dim):
    if my_config.get_option('dim_override', True):
        to_dim.ValueOverride = from_dim.ValueOverride

    if my_config.get_option('dim_textposition', False):
        to_dim.TextPosition = to_dim.Origin \
                              - (from_dim.Origin - from_dim.TextPosition)

    if my_config.get_option('dim_above', True):
        to_dim.Above = from_dim.Above
    if my_config.get_option('dim_below', True):
        to_dim.Below = from_dim.Below
    if my_config.get_option('dim_prefix', True):
        to_dim.Prefix = from_dim.Prefix
    if my_config.get_option('dim_suffix', True):
        to_dim.Suffix = from_dim.Suffix


def setup_style_per_config(from_style, to_style):
    # base
    if my_config.get_option('halftone', True):
        to_style.SetHalftone(from_style.Halftone)

    if my_config.get_option('transparency', True):
        to_style.SetSurfaceTransparency(from_style.Transparency)

    # projections
    if my_config.get_option('proj_line_color', True):
        to_style.SetProjectionLineColor(from_style.ProjectionLineColor)
    if my_config.get_option('proj_line_pattern', True):
        to_style.SetProjectionLinePatternId(from_style.ProjectionLinePatternId)
    if my_config.get_option('proj_line_weight', True):
        to_style.SetProjectionLineWeight(from_style.ProjectionLineWeight)

    if HOST_APP.is_newer_than(2019, or_equal=True):
        if my_config.get_option('proj_fill_color', True):
            to_style.SetSurfaceForegroundPatternColor(
                from_style.SurfaceForegroundPatternColor
                )
        if my_config.get_option('proj_fill_pattern', True):
            to_style.SetSurfaceForegroundPatternId(
                from_style.SurfaceForegroundPatternId
                )
        if my_config.get_option('proj_fill_pattern_visibility', True):
            to_style.SetSurfaceForegroundPatternVisible(
                from_style.IsSurfaceForegroundPatternVisible
                )
        if my_config.get_option('proj_bg_fill_color', True):
            to_style.SetSurfaceBackgroundPatternColor(
                from_style.SurfaceBackgroundPatternColor
                )
        if my_config.get_option('proj_bg_fill_pattern', True):
            to_style.SetSurfaceBackgroundPatternId(
                from_style.SurfaceBackgroundPatternId
                )
        if my_config.get_option('proj_bg_fill_pattern_visibility', True):
            to_style.SetSurfaceBackgroundPatternVisible(
                from_style.IsSurfaceBackgroundPatternVisible
                )
    else:
        if my_config.get_option('proj_fill_color', True):
            to_style.SetProjectionFillColor(
                from_style.ProjectionFillColor
                )
        if my_config.get_option('proj_fill_pattern', True):
            to_style.SetProjectionFillPatternId(
                from_style.ProjectionFillPatternId
                )
        if my_config.get_option('proj_fill_pattern_visibility', True):
            to_style.SetProjectionFillPatternVisible(
                from_style.IsProjectionFillPatternVisible
                )

    # cuts
    if my_config.get_option('cut_line_color', True):
        to_style.SetCutLineColor(from_style.CutLineColor)
    if my_config.get_option('cut_line_pattern', True):
        to_style.SetCutLinePatternId(from_style.CutLinePatternId)
    if my_config.get_option('cut_line_weight', True):
        to_style.SetCutLineWeight(from_style.CutLineWeight)

    if HOST_APP.is_newer_than(2019, or_equal=True):
        if my_config.get_option('cut_fill_color', True):
            to_style.SetCutForegroundPatternColor(
                from_style.CutForegroundPatternColor
                )
        if my_config.get_option('cut_fill_pattern', True):
            to_style.SetCutForegroundPatternId(
                from_style.CutForegroundPatternId
                )
        if my_config.get_option('cut_fill_pattern_visibility', True):
            to_style.SetCutForegroundPatternVisible(
                from_style.IsCutForegroundPatternVisible
                )
        if my_config.get_option('cut_bg_fill_color', True):
            to_style.SetCutBackgroundPatternColor(
                from_style.CutBackgroundPatternColor
                )
        if my_config.get_option('cut_bg_fill_pattern', True):
            to_style.SetCutBackgroundPatternId(
                from_style.CutBackgroundPatternId
                )
        if my_config.get_option('cut_bg_fill_pattern_visibility', True):
            to_style.SetCutBackgroundPatternVisible(
                from_style.IsCutBackgroundPatternVisible
                )
    else:
        if my_config.get_option('cut_fill_color', True):
            to_style.SetCutFillColor(
                from_style.CutFillColor
                )
        if my_config.get_option('cut_fill_pattern', True):
            to_style.SetCutFillPatternId(
                from_style.CutFillPatternId
                )
        if my_config.get_option('cut_fill_pattern_visibility', True):
            to_style.SetCutFillPatternVisible(
                from_style.IsCutFillPatternVisible
                )


def get_source_style(element_id):
    # get style of selected element
    from_style = revit.doc.ActiveView.GetElementOverrides(element_id)
    # make a new clean element style
    src_style = DB.OverrideGraphicSettings()
    # setup a new style per config and borrow from the selected element's style
    setup_style_per_config(from_style, src_style)
    return src_style


def pick_and_match_dim_overrides(src_dim_id):
    with forms.WarningBar(title='Pick dimensions to match overrides:'):
        src_dim = revit.doc.GetElement(src_dim_id)
        if src_dim.NumberOfSegments > 1:
            src_dim = src_dim.Segments[0]
        while True:
            dest_dim = revit.pick_element()

            if not dest_dim:
                break

            if isinstance(dest_dim, DB.Dimension):
                with revit.Transaction('Match Dimension Overrides'):
                    if dest_dim.NumberOfSegments > 1:
                        segments = dest_dim.Segments
                        for segment in segments:
                            setup_dim_overrides_per_config(src_dim, segment)
                    else:
                        setup_dim_overrides_per_config(src_dim, dest_dim)


def pick_and_match_styles(src_style):
    with forms.WarningBar(title='Pick objects to match overrides:'):
        while True:
            dest_element = revit.pick_element()

            if not dest_element:
                break

            dest_element_ids = [dest_element.Id]
            if hasattr(dest_element, 'GetSubComponentIds'):
                dest_element_ids.extend(dest_element.GetSubComponentIds())
            with revit.Transaction('Match Graphics Overrides'):
                for dest_elid in dest_element_ids:
                    revit.active_view.SetElementOverrides(dest_elid, src_style)


# FIXME: modify to remember source style
with forms.WarningBar(title='Pick source object:'):
    source_element = revit.pick_element()

if source_element:
    if isinstance(source_element, DB.Dimension):
        pick_and_match_dim_overrides(source_element.Id)
    else:
        source_style = get_source_style(source_element.Id)
        pick_and_match_styles(source_style)
