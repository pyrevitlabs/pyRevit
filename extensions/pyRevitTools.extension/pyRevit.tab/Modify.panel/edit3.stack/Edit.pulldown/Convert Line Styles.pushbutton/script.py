"""This is a tool to convert line styles. Run the tool,
select a line with the style to be replaced, and then
select a line with the interfacetypes style.
The script will correct the line styles in the model.
HOWEVER the lines that are part of a group will not be affected.
Also see the "Shake Filled Regions" tool.
"""
#pylint: disable=import-error,invalid-name,unused-argument,broad-except
from pyrevit.framework import List
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


NO_COLOR_COLOR = '#000000'


logger = script.get_logger()


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
        return self.category.Id.IntegerValue < 0

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
        self._setup_styles()

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

    def delete_linecats(self, line_converts):
        for style_convert in line_converts:
            for from_style in style_convert.from_styles:
                line_cat = from_style.category
                if line_cat:
                    try:
                        revit.doc.Delete(line_cat.Id)
                    except Exception as ex:
                        if line_cat.Id.IntegerValue < 0:
                            logger.error(
                                'Can not remove builtin line style \"%s\"',
                                line_cat.Name
                                )
                        logger.debug(
                            'Failed removing line category \"%s\" | %s',
                            line_cat.Name, ex
                            )

    def convert_styles(self, sender, args):
        self.Close()
        editable_lines = self.get_editable_lines()
        with revit.Transaction('Convert Line Styles'):
            for style_convert in self.line_converts:
                for eline in editable_lines:
                    style_convert.convert_style(eline)

            if self.deleteFromStyle.IsChecked:
                self.delete_linecats(self.line_converts)


if __name__ == '__main__':
    ConvertLineStylesWindow('ConvertLineStyles.xaml').show(modal=True)
