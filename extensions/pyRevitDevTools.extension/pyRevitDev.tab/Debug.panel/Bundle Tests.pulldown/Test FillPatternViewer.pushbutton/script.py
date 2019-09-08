#pylint: disable=C0111,E0401,C0103,W0201,W0613
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()
output = script.get_output()


class TestFillPatternViewer(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)
        self.pat_name_cb.ItemsSource = \
            sorted([x.GetFillPattern().Name
                    for x in revit.query.get_all_fillpattern_elements(
                        DB.FillPatternTarget.Drafting
                        )])
        self.pat_name_cb.SelectedIndex = 0

    def fill_pattern_changed(self, sender, args):
        selected_fillpattern = \
            revit.query.get_fillpattern_element(
                self.pat_name_cb.SelectedItem,
                DB.FillPatternTarget.Drafting
                ).GetFillPattern()
        if selected_fillpattern:
            self.fillpattern_control.FillPattern = selected_fillpattern


TestFillPatternViewer('TestFillPatternViewer.xaml').show(modal=True)
