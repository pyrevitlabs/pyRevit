"""This is a tool to convert line styles. Run the tool,
select a line with the style to be replaced, and then
select a line with the interfacetypes style.
The script will correct the line styles in the model.
HOWEVER the lines that are part of a group will not be affected.
Also see the "Shake Filled Regions" tool.

When retiring source styles, categories are kept (renamed + appearance
matched to the target) so Linework overrides that still reference them
do not leave the model in a crash-prone state. Hard deletion is unsafe
because the Revit API cannot remap Linework edge overrides.
"""
#pylint: disable=import-error,invalid-name,unused-argument,broad-except
from pyrevit.framework import List
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script
from pyrevit.compat import get_elementid_value_func


NO_COLOR_COLOR = '#000000'
RETIRE_PREFIX = 'zz_merged -> '


logger = script.get_logger()

get_elementid_value = get_elementid_value_func()


class StyleOption(object):
    def __init__(self, style):
        self.style = style

    def __str__(self):
        return '{} ({} {} {})'.format(
            self.name,
            self.weight,
            self.color_hex,
            self.pattern_name
            )

    def ToString(self):
        return str(self)

    @property
    def name(self):
        return self.style.Name

    @property
    def builtin(self):
        return get_elementid_value(self.category.Id) < 0

    @property
    def category(self):
        return self.style.GraphicsStyleCategory

    @property
    def weight(self):
        return self.category.GetLineWeight(DB.GraphicsStyleType.Projection)

    @property
    def color(self):
        if self.category.LineColor and self.category.LineColor.IsValid:
            return self.category.LineColor

    @property
    def color_hex(self):
        if self.color:
            return '#{:x02}{:x02}{:x02}'.format(self.color.Red,
                                                self.color.Green,
                                                self.color.Blue)
        else:
            return NO_COLOR_COLOR

    @property
    def pattern(self):
        return self.style.Document.GetElement(
            self.category.GetLinePatternId(DB.GraphicsStyleType.Projection)
            )

    @property
    def pattern_name(self):
        return self.pattern.Name if self.pattern else 'Solid'


class StyleConvert(object):
    def __init__(self, to_style):
        self.to_style = to_style
        self.from_styles = []

    @property
    def name(self):
        return self.to_style.name

    @property
    def builtin(self):
        return self.to_style.builtin

    @property
    def category(self):
        return self.to_style.category

    @property
    def weight(self):
        return self.to_style.weight

    @property
    def color(self):
        return self.to_style.color

    @property
    def color_hex(self):
        return self.to_style.color_hex

    @property
    def pattern(self):
        return self.to_style.pattern

    @property
    def pattern_name(self):
        return self.to_style.pattern_name

    def add_from_style(self, from_style):
        if from_style not in self.from_styles:
            self.from_styles.append(from_style)

    def convert_style(self, line_element):
        for from_style in self.from_styles:
            if line_element.LineStyle.Name == from_style.name:
                line_element.LineStyle = self.to_style.style


class ConvertLineStylesWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)
        self.Closing += self.Close_Click
        self._setup_styles()


    def Close_Click(self, sender, args):
        pass

    def _setup_styles(self):
        self._styles = revit.query.get_line_styles(doc=revit.doc)
        self._styleops = [StyleOption(x) for x in self._styles]
        self.fromStyles.ItemsSource = \
            sorted(self._styleops, key=lambda x: x.name)
        self.toStyles.ItemsSource = self.fromStyles.ItemsSource
        self.convertList.ItemsSource = []

    @property
    def from_style(self):
        return self.fromStyles.SelectedItem

    @property
    def to_style(self):
        return self.toStyles.SelectedItem

    @property
    def line_converts(self):
        return list(self.convertList.ItemsSource)

    @property
    def convert_detaillines(self):
        return self.convertDetailLines.IsChecked

    @property
    def convert_modellines(self):
        return self.convertModelLines.IsChecked

    @property
    def convert_sketchlines(self):
        return self.convertSketchLines.IsChecked

    def style_selection_changed(self, sender, args):
        if self.from_style and self.to_style:
            self.addConvert_b.IsEnabled = True
        else:
            self.addConvert_b.IsEnabled = False

    def get_editable_lines(self):
        """Return list of lines for style convertping."""
        mc_filter = \
            DB.ElementMulticategoryFilter(
                List[DB.BuiltInCategory](
                    [
                        DB.BuiltInCategory.OST_Lines,
                        DB.BuiltInCategory.OST_SketchLines
                    ])
                )

        tline_cl = DB.FilteredElementCollector(revit.doc)\
                    .WherePasses(mc_filter)\
                    .WhereElementIsNotElementType()\
                    .ToElements()

        lines = []
        conv_detlines = self.convert_detaillines
        conv_modlines = self.convert_modellines
        conv_skhlines = self.convert_sketchlines
        for tline in tline_cl:
            # skip grouped lines
            if tline.GroupId is None \
                    or tline.GroupId == DB.ElementId.InvalidElementId:
                # sketchlines could be detail or model so process first
                # but only detail sketchlines are editable
                if revit.query.is_detail_curve(tline):
                    if revit.query.is_sketch_curve(tline):
                        if not conv_skhlines:
                            continue
                    elif not conv_detlines:
                        continue

                elif revit.query.is_model_curve(tline) and not conv_modlines:
                    continue

                lines.append(tline)

        return lines

    def add_convert(self, sender, args):
        processed = False
        existing_converts = self.convertList.ItemsSource
        for convert in existing_converts:
            if convert.to_style.name == self.to_style.name:
                convert.add_from_style(self.from_style)
                processed = True
        if not processed:
            style_convert = StyleConvert(self.to_style)
            style_convert.add_from_style(self.from_style)
            existing_converts.append(style_convert)

        # refresh convert tree
        self.convertList.ItemsSource = []
        self.convertList.ItemsSource = existing_converts

    def convert_up(self, sender, args):
        pass

    def convert_clear(self, sender, args):
        pass

    def convert_down(self, sender, args):
        pass

    def _collect_line_categories(self):
        lines_cat = revit.doc.Settings.Categories.get_Item(
            DB.BuiltInCategory.OST_Lines
            )
        return list(lines_cat.SubCategories)

    def _unique_retire_name(self, from_name, to_name, existing_names):
        base = '{}{} => {}'.format(RETIRE_PREFIX, from_name, to_name)
        name = base
        index = 2
        while name in existing_names:
            name = '{} ({})'.format(base, index)
            index += 1
        return name

    def _copy_category_graphics(self, from_cat, to_cat):
        for style_type in (DB.GraphicsStyleType.Projection,
                           DB.GraphicsStyleType.Cut):
            try:
                weight = to_cat.GetLineWeight(style_type)
                if weight and weight > 0:
                    from_cat.SetLineWeight(weight, style_type)
            except Exception as ex:
                logger.debug(
                    'Failed copying line weight for \"%s\" | %s',
                    from_cat.Name, ex
                    )
            try:
                pattern_id = to_cat.GetLinePatternId(style_type)
                if pattern_id is not None:
                    from_cat.SetLinePatternId(pattern_id, style_type)
            except Exception as ex:
                logger.debug(
                    'Failed copying line pattern for \"%s\" | %s',
                    from_cat.Name, ex
                    )
        try:
            if to_cat.LineColor and to_cat.LineColor.IsValid:
                from_cat.LineColor = to_cat.LineColor
        except Exception as ex:
            logger.debug(
                'Failed copying line color for \"%s\" | %s',
                from_cat.Name, ex
                )

    def _remap_mep_hidden_line_styles(self, line_converts):
        # Project MEP hidden-line setting can reference a custom style; deleting
        # that style without remapping can destabilize the document.
        try:
            mep_settings = DB.MEPHiddenLineSettings.GetMEPHiddenLineSettings(
                revit.doc
                )
        except Exception:
            return

        if not mep_settings:
            return

        current_id = mep_settings.LineStyle
        if not current_id or current_id == DB.ElementId.InvalidElementId:
            return

        current_value = get_elementid_value(current_id)
        for style_convert in line_converts:
            for from_style in style_convert.from_styles:
                if get_elementid_value(from_style.style.Id) == current_value:
                    try:
                        mep_settings.LineStyle = style_convert.to_style.style.Id
                        logger.info(
                            'Remapped MEP hidden line style \"%s\" -> \"%s\"',
                            from_style.name,
                            style_convert.to_style.name
                            )
                    except Exception as ex:
                        logger.warning(
                            'Could not remap MEP hidden line style \"%s\" | %s',
                            from_style.name, ex
                            )
                    return

    def _remap_remaining_curve_styles(self, line_converts):
        # Convert any leftover CurveElements still on source styles (e.g. types
        # skipped by convert options). Grouped curves may refuse edits.
        from_names = {}
        for style_convert in line_converts:
            for from_style in style_convert.from_styles:
                from_names[from_style.name] = style_convert.to_style.style

        if not from_names:
            return

        curves = DB.FilteredElementCollector(revit.doc)\
            .OfClass(DB.CurveElement)\
            .WhereElementIsNotElementType()\
            .ToElements()

        for curve in curves:
            # keep grouped curves unchanged (consistent with primary conversion pass)
            if curve.GroupId is not None \
                    and curve.GroupId != DB.ElementId.InvalidElementId:
                continue
            try:
                style_name = curve.LineStyle.Name
            except Exception:
                continue
            to_style = from_names.get(style_name)
            if not to_style:
                continue
            try:
                curve.LineStyle = to_style
            except Exception as ex:
                logger.debug(
                    'Could not remap curve %s style \"%s\" | %s',
                    get_elementid_value(curve.Id), style_name, ex
                    )

    def retire_linecats(self, line_converts):
        """Match source style look to target and rename; keep ElementIds."""
        existing_names = set(
            cat.Name for cat in self._collect_line_categories()
            )

        for style_convert in line_converts:
            to_cat = style_convert.to_style.category
            for from_style in style_convert.from_styles:
                from_cat = from_style.category
                if not from_cat:
                    continue
                if get_elementid_value(from_cat.Id) < 0:
                    logger.warning(
                        'Skipping builtin line style \"%s\"',
                        from_cat.Name
                        )
                    continue
                old_name = from_cat.Name
                try:
                    self._copy_category_graphics(from_cat, to_cat)
                    new_name = self._unique_retire_name(
                        old_name,
                        style_convert.to_style.name,
                        existing_names
                        )
                    from_cat.Name = new_name
                    existing_names.add(new_name)
                    logger.info(
                        'Retired line style \"%s\" as \"%s\"',
                        old_name, new_name
                        )
                except Exception as ex:
                    logger.warning(
                        'Failed retiring line style \"%s\" | %s',
                        old_name, ex
                        )

    def convert_styles(self, sender, args):
        self.Close()
        editable_lines = self.get_editable_lines()
        with revit.Transaction('Convert Line Styles'):
            for style_convert in self.line_converts:
                for eline in editable_lines:
                    style_convert.convert_style(eline)

            if self.deleteFromStyle.IsChecked:
                self._remap_remaining_curve_styles(self.line_converts)
                self._remap_mep_hidden_line_styles(self.line_converts)
                self.retire_linecats(self.line_converts)


if __name__ == '__main__':
    ConvertLineStylesWindow('ConvertLineStyles.xaml').show(modal=True)
