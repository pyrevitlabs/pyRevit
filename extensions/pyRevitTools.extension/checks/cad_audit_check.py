# -*- coding: utf-8 -*-

from pyrevit import script, revit, DB, DOCS

from pyrevit.preflight import PreflightTestCase

from System.Windows import Window # Used for cancel button
from rpw.ui.forms import (FlexForm, Label, Separator, Button) # RPW
from rpw.ui.forms.flexform import RpwControlMixin, Controls # Used to create RadioButton

from pyrevit.coreutils import Timer # Used for timing the check
from datetime import timedelta # Used for timing the check

doc = DOCS.doc
ac_view = doc.ActiveView


def collect_cadinstances(active_view_only):
    """     Collect ImportInstance class from whole model or from just active view  """
    collector = DB.FilteredElementCollector(doc, ac_view.Id) if active_view_only else DB.FilteredElementCollector(doc)
    cadinstances = collector.OfClass(DB.ImportInstance).WhereElementIsNotElementType().ToElements()
    if cadinstances:
        return cadinstances


# Manage Flexform cancel using .NET System.Windows RoutedEventArgs Class
def cancel_clicked(sender, e):
    window = Window.GetWindow(sender)
    window.close()
    script.exit()

# Add radio button functionality to RPW Flexforms
class RadioButton(RpwControlMixin, Controls.RadioButton):
    """
    Windows.Controls.RadioButton Wrapper

    >>> RadioButton('Label')
    """
    def __init__(self, name, radio_text, default=False, **kwargs):
        """
        Args:
            name (``str``): Name of control. Will be used to return value
            radio_text (``str``): RadioButton label Text
            default (``bool``): Sets IsChecked state [Default: False]
            wpf_params (kwargs): Additional WPF attributes
        """
        self.Name = name
        self.Content = radio_text
        self.IsChecked = default
        self.set_attrs(top_offset=0, **kwargs)

    @property
    def value(self):
        return self.IsChecked
    
def get_cad_site(cad_inst):
    """ A CAD's location site cannot be got from the Shared Site parameter 
        cad_inst.Name returns the site name with a 'location' prefix (language-specific, eg 'emplacement' in French)"""
    return cad_inst.Name.replace("location", "-")


def get_user_input():
    """ create RPW input FlexForm for user choice of collection mode (coll_mode) whole model or just active view """
    flexform_comp = [
        Label("Audit CAD instances:"),
        RadioButton("model", "in this project", True, GroupName="grp"), # GroupName implemented in class through kwargs
        RadioButton("active_view", "in only the active view", False, GroupName="grp"),
        Separator(),
        Button("CANCEL", on_click=cancel_clicked),
        Button("OK"),
    ]

    user_input = FlexForm("Audit of CAD instances in the current project", flexform_comp, Width=500, Height=200) # returns a FlexForm object
    user_input.show()
    user_input_dict = user_input.values # This is a dictionary
    if not user_input_dict:
        script.exit()

    return user_input_dict

def get_load_stat(cad, is_link):
    """ Loaded status from the import instance's CADLinkType """
    cad_type = doc.GetElement(cad.GetTypeId()) # Retreive the type from the instance
    
    if not is_link:
        return ":warning: IMPORTED"
        
    try:
        exfs = cad_type.GetExternalFileReference()
        if not exfs:
            return ":warning: IMPORTED"
        status = exfs.GetLinkedFileStatus().ToString()
    except Exception:
        # Fallback for cloud-based CAD links (ACC/ADC)
        exfs = cad_type.GetExternalResourceReferences()
        ext_ref = next(iter(exfs.Values)) if exfs.Count > 0 else None
        if not ext_ref:
            return ":warning: IMPORTED"
        status = ext_ref.GetResourceVersionStatus().ToString()

    if not exfs:
        return ":warning: IMPORTED" # Not an external reference
    
    if status == "Loaded":
        return ":ballot_box_with_check: Loaded"
    if status == "NotFound":
        return ":cross_mark: NotFound"
    if status == "Unloaded":
        return ":heavy_multiplication_x: Unloaded"
    if status == "OutOfDate":
        return ":warning: Outdated on ADC"
    if  status == "Current":
        return ":ballot_box_with_check: Current on ADC"
    raise ValueError("Unexpected status {}".format(status))


def check_model(doc, output):
    timer = Timer()
    output = script.get_output()
    output.close_others()
    output.set_title("CAD audit of model '{}'".format(doc.Title))
    output.set_width (1700)
    
    coll_mode = get_user_input()["active_view"]
    
    table_data = [] # store array for table formatted output
    row_head = ["No", "Select/Zoom", "DWG instance", "Loaded status", "Workplane or single view", "Duplicate", "Workset", "Creator user", "Location site name"] # output table first and last row
    row_no_cad = ["-", "-", "No CAD instances found", "-", "-", "-", "-", "-", "-"] # output table row for when no CAD found
    cad_instances = collect_cadinstances(coll_mode)
    if not cad_instances:
        table_data.append(row_no_cad)
    else:
        for count, cad in enumerate(cad_instances, start=1):
            cad_id = cad.Id
            cad_is_link = cad.IsLinked
            cad_name = cad.Parameter[DB.BuiltInParameter.IMPORT_SYMBOL_NAME].AsString()
    
            table_row = [
                count,
                output.linkify(cad_id, title="Select"),
                cad_name,
                get_load_stat(cad, cad.IsLinked), # loaded status
            ]
    
            # if the instance has an owner view, it was placed on the active view only (bad, so give warning and show the view name)
            # if the instance has no owner view, it should have a level or workplane (good)
            cad_own_view_id = cad.OwnerViewId
            if cad_own_view_id == DB.ElementId.InvalidElementId:
                table_row.append(doc.GetElement(cad.LevelId).Name)
            else:
                cad_own_view_name = doc.GetElement(cad_own_view_id).Name
                table_row.append(":warning: view '{}'".format(cad_own_view_name))
            table_row.append(":warning:" if cad_name in [row[2] for row in table_data] else "-") # If the name is already in table_data, it is a duplicat (bad)
            table_row.append(revit.query.get_element_workset(cad).Name) # cad instance workset
            table_row.append(DB.WorksharingUtils.GetWorksharingTooltipInfo(revit.doc, cad.Id).Creator) # ID of the user
            table_row.append(get_cad_site(cad)) # Extract site name from location
            table_data.append(table_row)
    table_data.append(row_head)  
    output.print_md("## Preflight audit of imported and linked CAD")
    output.print_table(table_data=table_data,
                   title="",
                   columns=row_head,
                   formats=['', '', '', '', '', '', '', '', ''],
                   last_line_style='background-color:#233749;color:white;font-weight:bold')
    
    # Summary output section:
    link_to_view = output.linkify(ac_view.Id, title="Show the view")
    print("{} CAD instances found.".format(len(cad_instances or [])))
    if coll_mode: # if active view only
        summary_msg = "the active view ('{}') {}".format(ac_view.Name, link_to_view)
    else:
        summary_msg = "the whole model ({})".format(doc.Title)
    print("The check was run on {}".format(summary_msg))
    output.print_md("##Explanations for warnings :warning:")
    print("Loaded status...........: alert if a CAD is imported, rather than linked")
    print("Workplane or single view: alert if a CAD is placed on a single view with the option 'active view only' rather than on a model workplane")
    print("Duplicate...............: alert if a CAD is placed more than once (whether linked or imported) in case it is unintentinal")

    # Display check duration
    endtime = timer.get_time()
    endtime_hms = str(timedelta(seconds=endtime))
    endtime_hms_claim = " \n\nCheck duration " + endtime_hms[0:7] # Remove seconods decimals from string
    print(endtime_hms_claim)

class ModelChecker(PreflightTestCase):
    """
    Preflight audit of imported and linked CAD
    This QC tools returns the following data:
        CAD link instance and type information

        Quality control includes information and alerts for:
          The status of links (Loaded, Not found, Unloaded...)
          Whether a CAD is on a model workplane or just a single view
          Whether a CAD is linked or imported
          Whether CADs have been duplicated
          The CAD's shared location name

          Feature: The output allows navigating to the found CADs

    """

    name = "CAD Audit"
    author = "Kevin Salmon"


    def startTest(self, doc, output):
        check_model(doc, output)
