# -*- coding: utf-8 -*-

from pyrevit import script, revit, DB, DOCS

import sys
import os
# Add current directory to path for local imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from pyrevit.preflight import PreflightTestCase
from check_translations import DocstringMeta

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
    from check_translations import get_check_translation
    flexform_comp = [
        Label(get_check_translation("CADAuditInstances")),
        RadioButton("model", get_check_translation("CADAuditInProject"), True, GroupName="grp"), # GroupName implemented in class through kwargs
        RadioButton("active_view", get_check_translation("CADAuditInActiveView"), False, GroupName="grp"),
        Separator(),
        Button(get_check_translation("CADAuditCancel"), on_click=cancel_clicked),
        Button(get_check_translation("CADAuditOK")),
    ]

    user_input = FlexForm(get_check_translation("CADAuditTitle"), flexform_comp, Width=500, Height=200) # returns a FlexForm object
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
    
    from check_translations import get_check_translation
    table_data = [] # store array for table formatted output
    row_head = [
        get_check_translation("CADAuditNo"),
        get_check_translation("CADAuditSelectZoom"),
        get_check_translation("CADAuditDWGInstance"),
        get_check_translation("CADAuditLoadedStatus"),
        get_check_translation("CADAuditWorkplaneOrView"),
        get_check_translation("CADAuditDuplicate"),
        get_check_translation("AuditAllWorksets"),
        get_check_translation("CADAuditCreatorUser"),
        get_check_translation("CADAuditLocationSiteName")
    ] # output table first and last row
    row_no_cad = ["-", "-", get_check_translation("CADAuditNoInstances"), "-", "-", "-", "-", "-", "-"] # output table row for when no CAD found
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
                output.linkify(cad_id, title=get_check_translation("CADAuditSelect")),
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
    output.print_md("## {}".format(get_check_translation("CADAuditPreflightAudit")))
    output.print_table(table_data=table_data,
                   title="",
                   columns=row_head,
                   formats=['', '', '', '', '', '', '', '', ''],
                   last_line_style='background-color:#233749;color:white;font-weight:bold')
    
    # Summary output section:
    link_to_view = output.linkify(ac_view.Id, title=get_check_translation("CADAuditShowView"))
    print("{} {}".format(len(cad_instances or []), get_check_translation("CADAuditInstancesFound")))
    if coll_mode: # if active view only
        summary_msg = "{} ('{}') {}".format(get_check_translation("CADAuditActiveView"), ac_view.Name, link_to_view)
    else:
        summary_msg = "{} ({})".format(get_check_translation("CADAuditWholeModel"), doc.Title)
    print("{} {}".format(get_check_translation("CADAuditCheckRunOn"), summary_msg))
    output.print_md("##{} :warning:".format(get_check_translation("CADAuditExplanations")))
    print(get_check_translation("CADAuditLoadedStatusExplanation"))
    print(get_check_translation("CADAuditWorkplaneExplanation"))
    print(get_check_translation("CADAuditDuplicateExplanation"))

    # Display check duration
    endtime = timer.get_time()
    endtime_hms = str(timedelta(seconds=endtime))
    endtime_hms_claim = " \n\n{} {}".format(get_check_translation("CADAuditCheckDuration"), endtime_hms[0:7]) # Remove seconods decimals from string
    print(endtime_hms_claim)

class ModelChecker(PreflightTestCase):
    __metaclass__ = DocstringMeta
    _docstring_key = "CheckDescription_CADAudit"
    
    @property
    def name(self):
        from check_translations import get_check_translation
        return get_check_translation("CheckName_CADAudit")
    
    author = "Kevin Salmon"


    def startTest(self, doc, output):
        check_model(doc, output)
