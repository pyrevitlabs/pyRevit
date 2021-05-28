"""Journal content templates"""
#pylint: disable=line-too-long
# initializtion templates ------------------------------------------------------
# timestamp format: 27-Oct-2016 19:33:31.459
INIT = """' revit_journal_maker generated journal
' 0:< 'C {time_stamp};
Dim Jrn
Set Jrn = CrsJournalScript
"""


# initializing the journal in debug permissive mode
INIT_DEBUG = """' Adding debug options'
Jrn.Directive "DebugMode", "PerformAutomaticActionInErrorDialog", {takedefaultaction}
Jrn.Directive "DebugMode", "PermissiveJournal", {permissive}
' Jrn.Directive "DebugMode", "PermissiveJournalAndReportAsError", {permissive_jrn}
' Jrn.Directive "DebugMode" , "GfxUseDx9AccelerationOnPlay" , {usedx9accel}
"""


# new file templates -----------------------------------------------------------
# template for creating a new model
NEW_MODEL = """' Create new model
Jrn.Command "Ribbon" , "Create a new project , ID_FILE_NEW_CHOOSE_TEMPLATE"
Jrn.ComboBox "Modal , New Project , Dialog_Revit_NewProject" _
    , "Control_Revit_TemplateCombo" _
    , "Select" , "{template_name}"
Jrn.RadioButton "Modal , New Project , Dialog_Revit_NewProject" _
    , "Project, Control_Revit_RadioNewProject"
Jrn.PushButton "Modal , New Project , Dialog_Revit_NewProject" _
    , "OK, IDOK"
"""

# template for creating a new template model
NEW_MODEL_TEMPLATE = """' Create new template model
Jrn.Command "Ribbon" , "Create a new project , ID_FILE_NEW_CHOOSE_TEMPLATE"
Jrn.ComboBox "Modal , New Project , Dialog_Revit_NewProject" _
    , "Control_Revit_TemplateCombo" _
    , "Select" , "{template_name}"
Jrn.RadioButton "Modal , New Project , Dialog_Revit_NewProject" _
    , "Project template, Control_Revit_RadioNewTemplate"
Jrn.PushButton "Modal , New Project , Dialog_Revit_NewProject" _
    , "OK, IDOK"
"""


# template for creating a new family
NEW_FAMILY = """' Create new family model
Jrn.Command "Ribbon" , "Create a new family , ID_FAMILY_NEW"
"""


# template for creating a new conceptual mass
NEW_CONCEPTUAL_MASS = """' Create new conceptual mass
Jrn.Command "Ribbon" , "Create a new conceptual mass , ID_NEW_REVIT_DESIGN_MODEL"
"""


# template for creating a new title block
NEW_TITLEBLOCK = """' Create new family model
Jrn.Command "Ribbon" , "Create a new titleblock , ID_TITLEBLOCK_NEW"
"""


# template for creating a new annotation symbol
NEW_ANNOTATION_SYM = """' Create new family model
Jrn.Command "Ribbon" , "Create a new annotation symbol family , ID_ANNOTATION_SYMBOL_NEW"
"""


# template for responding to Revit GUI when asking for template file
NEW_FROM_RFT = """' Get input rft file
Jrn.Data "FileDialog"  _
    , "IDOK", "{rft_file_path}", "rft" _
    , "{rft_file_name}", "{rft_file_name}"
Jrn.Data "FileType"  _
    , "Family Template Files (*.rft)"
"""


# open model templates ---------------------------------------------------------
# template for open & detaching workshared model
CENTRAL_OPEN_DETACH = """' Opening workshared model as detached
Jrn.Command "Ribbon" , "Open an existing project , ID_REVIT_FILE_OPEN"
Jrn.Data "FileOpenSubDialog" , "OpenAsLocalCheckBox", "True"
Jrn.Data "FileOpenSubDialog" , "DetachCheckBox", "True"
Jrn.Data "FileOpenSubDialog" , "OpenAsLocalCheckBox", "False"
Jrn.Data "File Name" , "IDOK", "{model_path}"
Jrn.Data "WorksetConfig" , "Custom", {workset_config}
Jrn.PushButton "Modal , Opening Worksets , Dialog_Revit_Partitions", "OK, IDOK"
Jrn.Data "TaskDialogResult" _
    , "Detaching this model will create an independent model. You will be unable to synchronize your changes with the original central model." & vbLf & "What do you want to do?", "Detach and preserve worksets", "1001"
Jrn.Directive "DocSymbol" , "[]"
"""


# template for open & detach & auditing workshared model
CENTRAL_OPEN_DETACH_AUDIT = """' Opening workshared model as detached and audit
Jrn.Command "Ribbon" , "Open an existing project , ID_REVIT_FILE_OPEN"
Jrn.Data "FileOpenSubDialog" , "OpenAsLocalCheckBox", "True"
Jrn.Data "FileOpenSubDialog" , "DetachCheckBox", "True"
Jrn.Data "FileOpenSubDialog" , "OpenAsLocalCheckBox", "False"
Jrn.Data "FileOpenSubDialog" , "AuditCheckBox", "True"
Jrn.Data "TaskDialogResult"  _
    , "This operation can take a long time. Recommended use includes periodic maintenance of large files and preparation for upgrading to a new release. Do you want to continue?",  _
    "Yes", "IDYES"
Jrn.Data "File Name" , "IDOK", "{model_path}"
Jrn.Data "WorksetConfig" , "Custom", {workset_config}
Jrn.PushButton "Modal , Opening Worksets , Dialog_Revit_Partitions", "OK, IDOK"
Jrn.Data "TaskDialogResult" _
    , "Detaching this model will create an independent model. You will be unable to synchronize your changes with the original central model." & vbLf & "What do you want to do?" _
    , "Detach and preserve worksets", "1001"
Jrn.Directive "DocSymbol" , "[]"
"""


# template for open & detach & discard worksets workshared model
CENTRAL_OPEN_DETACH_DISCARD = """' Opening workshared model as detached and discard worksets
Jrn.Command "Ribbon" , "Open an existing project , ID_REVIT_FILE_OPEN"
Jrn.Data "FileOpenSubDialog" , "OpenAsLocalCheckBox", "True"
Jrn.Data "FileOpenSubDialog" , "DetachCheckBox", "True"
Jrn.Data "FileOpenSubDialog" , "OpenAsLocalCheckBox", "False"
Jrn.Data "FileOpenSubDialog" , "AuditCheckBox", "False"
Jrn.Data "File Name" , "IDOK", "{model_path}"
Jrn.Data "WorksetConfig" , "Custom", {workset_config}
Jrn.PushButton "Modal , Opening Worksets , Dialog_Revit_Partitions", "OK, IDOK"
Jrn.Data "TaskDialogResult" _
    , "Detaching this model will create an independent model. You will be unable to synchronize your changes with the original central model." & vbLf & "What do you want to do?" _
    , "Detach and discard worksets", "1002"
Jrn.Directive "DocSymbol" , "[]"
"""


# template for open & detach & audit & discard worksets workshared model
CENTRAL_OPEN_DETACH_AUDIT_DISCARD = """' Opening workshared model as detached and discard worksets and audit
Jrn.Command "Ribbon" , "Open an existing project , ID_REVIT_FILE_OPEN"
Jrn.Data "FileOpenSubDialog" , "OpenAsLocalCheckBox", "True"
Jrn.Data "FileOpenSubDialog" , "DetachCheckBox", "True"
Jrn.Data "FileOpenSubDialog" , "OpenAsLocalCheckBox", "False"
Jrn.Data "FileOpenSubDialog" , "AuditCheckBox", "True"
Jrn.Data "TaskDialogResult"  _
    , "This operation can take a long time. Recommended use includes periodic maintenance of large files and preparation for upgrading to a new release. Do you want to continue?",  _
    "Yes", "IDYES"
Jrn.Data "File Name" , "IDOK", "{model_path}"
Jrn.Data "WorksetConfig" , "Custom", {workset_config}
Jrn.PushButton "Modal , Opening Worksets , Dialog_Revit_Partitions", "OK, IDOK"
Jrn.Data "TaskDialogResult" _
    , "Detaching this model will create an independent model. You will be unable to synchronize your changes with the original central model." & vbLf & "What do you want to do?" _
    , "Detach and discard worksets", "1002"
Jrn.Directive "DocSymbol" , "[]"
"""


# template for opening the central model of a workshared model
CENTRAL_OPEN = """' Opening workshared model as central
Jrn.Command "Ribbon" , "Open an existing project , ID_REVIT_FILE_OPEN"
Jrn.Data "FileOpenSubDialog" , "OpenAsLocalCheckBox", "False"
Jrn.Data "FileOpenSubDialog" , "AuditCheckBox", "False"
Jrn.Data "File Name" , "IDOK", "{model_path}"
Jrn.Data "WorksetConfig" , "Custom", {workset_config}
Jrn.PushButton "Modal , Opening Worksets , Dialog_Revit_Partitions", "OK, IDOK"
Jrn.Directive "DocSymbol" , "[]"
"""


# template for open & audit the central model of a workshared model
CENTRAL_OPEN_AUDIT = """' Opening workshared model as central
Jrn.Command "Ribbon" , "Open an existing project , ID_REVIT_FILE_OPEN"
Jrn.Data "FileOpenSubDialog" , "OpenAsLocalCheckBox", "False"
Jrn.Data "FileOpenSubDialog" , "AuditCheckBox", "True"
Jrn.Data "TaskDialogResult"  _
    , "This operation can take a long time. Recommended use includes periodic maintenance of large files and preparation for upgrading to a new release. Do you want to continue?",  _
    "Yes", "IDYES"
Jrn.Data "File Name" , "IDOK", "{model_path}"
Jrn.Data "WorksetConfig" , "Custom", {workset_config}
Jrn.PushButton "Modal , Opening Worksets , Dialog_Revit_Partitions", "OK, IDOK"
Jrn.Directive "DocSymbol" , "[]"
"""


# template for opening a workshared model
WORKSHARED_OPEN = """' Opening non-workshared model
Jrn.Command "Ribbon" , "Open an existing project , ID_REVIT_FILE_OPEN"
Jrn.Data "FileOpenSubDialog" , "AuditCheckBox", "False"
Jrn.Data "File Name" , "IDOK", "{model_path}"
Jrn.Data "WorksetConfig" , "Custom", {workset_config}
Jrn.PushButton "Modal , Opening Worksets , Dialog_Revit_Partitions", "OK, IDOK"
Jrn.Directive "DocSymbol" , "[]"
"""


# template for open & auditing a workshared model
WORKSHARED_OPEN_AUDIT = """' Opening non-workshared model and audit
Jrn.Command "Ribbon" , "Open an existing project , ID_REVIT_FILE_OPEN"
Jrn.Data "FileOpenSubDialog" , "AuditCheckBox", "True"
Jrn.Data "TaskDialogResult"  _
    , "This operation can take a long time. Recommended use includes periodic maintenance of large files and preparation for upgrading to a new release. Do you want to continue?",  _
    "Yes", "IDYES"
Jrn.Data "File Name" , "IDOK", "{model_path}"
Jrn.Data "WorksetConfig" , "Custom", {workset_config}
Jrn.PushButton "Modal , Opening Worksets , Dialog_Revit_Partitions", "OK, IDOK"
Jrn.Directive "DocSymbol" , "[]"
"""


# template for opening a non-workshared model
FILE_OPEN = """' Opening non-workshared model
Jrn.Command "Ribbon" , "Open an existing project , ID_REVIT_FILE_OPEN"
Jrn.Data "FileOpenSubDialog" , "AuditCheckBox", "False"
Jrn.Data "File Name" , "IDOK", "{model_path}"
Jrn.Data "WorksetConfig" , "Custom", 0
Jrn.Directive "DocSymbol" , "[]"
"""


# template for open & audit a non-workshared model
FILE_OPEN_AUDIT = """' Opening non-workshared model and audit
Jrn.Command "Ribbon" , "Open an existing project , ID_REVIT_FILE_OPEN"
Jrn.Data "FileOpenSubDialog" , "AuditCheckBox", "True"
Jrn.Data "TaskDialogResult"  _
    , "This operation can take a long time. Recommended use includes periodic maintenance of large files and preparation for upgrading to a new release. Do you want to continue?",  _
    "Yes", "IDYES"
Jrn.Data "File Name" , "IDOK", "{model_path}"
Jrn.Data "WorksetConfig" , "Custom", 0
Jrn.Directive "DocSymbol" , "[]"
"""


# misc templates ---------------------------------------------------------------
# template for executing an external command
EXTERNAL_COMMAND = """' Executing external command
Jrn.RibbonEvent "TabActivated:{external_command_tab}"
Jrn.RibbonEvent "Execute external command:CustomCtrl_%CustomCtrl_%{external_command_tab}%{external_command_panel}%{command_class_name}:{command_class}"
"""

# template for providing data to an external command
EXTERNAL_COMMANDDATA = """' Providing command data to external command
Jrn.Data "APIStringStringMapJournalData"  _
    , {data_count} _
    , {data_string}
"""


# template for executing a Dynamo script
DYNAMO_COMMAND = """' Executing Dynamo
Jrn.RibbonEvent "TabActivated:Manage"
Jrn.Command "Ribbon" , "Launch Dynamo, ID_VISUAL_PROGRAMMING_DYNAMO"
Jrn.Data "APIStringStringMapJournalData"  _
    , 5 _
    , "dynPath", "{dynamo_def_path}" _
    , "dynShowUI", "{dyn_show_ui}" _
    , "dynAutomation", "{dyn_automation}" _
    , "dynPathExecute", "{dyn_path_exec}" _
    , "dynModelShutDown", "{dyn_shutdown}"
"""


# template for importing a family
IMPORT_FAMILY = """' Importing family
Jrn.Command "Ribbon" , "Load a family into the project , ID_FAMILY_LOAD"
Jrn.Data "File Name"  _
    , "IDOK", "{family_file}"
Jrn.Data "FileExternalTypes"  _
    , ""
Jrn.Data "Transaction Successful"  _
    , "Load Family"
"""


# not working - needs count and list of all view and sheets
EXPORT_CAD = """
Jrn.Command "Ribbon" , " , ID_EXPORT_DWG"
Jrn.ComboBox "Modal , DWG Export , Dialog_Revit_AdrExportPersistentDlg" _
    , "Control_Revit_CBExportSettings" _
    , "Select" , "<in-session export setup>"
    , "Select" , "{export_setup_config}"
Jrn.ComboBox "Modal , DWG Export , Dialog_Revit_AdrExportPersistentDlg" _
    , "Control_Revit_ExportSet" _
    , "Select" , "<current view/sheet only>"
    , "Select" , "<in-session view/sheet set>"
    , "Select" , "{export_sheet_set}"
Jrn.PushButton "Modal , DWG Export , Dialog_Revit_AdrExportPersistentDlg" _
    , "Next..., IDOK"
Jrn.Data "Export File Answer", "IDOK"
Jrn.Data "Export Number Of Views", "{export_view_count}"
' this line will repeat depending on number of views or sheets exported
[Jrn.Data "Export View Names", "{export_view_or_sheet_name}"]
' 0 or 1
Jrn.Data "Export As Single File", "{export_single}"
Jrn.Data "Export File Name Type", "2"
Jrn.Data "Export File Name", "1"
Jrn.Data "Export File Name", "{export_file_path}"
"""


# template for closing file and Revit
FILE_CLOSE = """' Closing model
Jrn.Command "SystemMenu" , "Quit the application; prompts to save projects , ID_APP_EXIT"
Jrn.Data "TaskDialogResult" , "Do you want to save changes to Untitled?", "No", "IDNO"
"""


# template for saving non-workshared model
FILE_SAVE = """' Saving model
Jrn.Command "Ribbon" , "Save the active project , ID_REVIT_FILE_SAVE"
"""


# template for syncinc workshared model
FILE_SYNC_START = """' Syncing model
Jrn.Command "Ribbon" , "Save the active project back to the Central Model , ID_FILE_SAVE_TO_MASTER"
"""

# template options for syncinc workshared model
FILE_SYNC_COMPACT = """' Set compact central checkbox to {compact_central}
Jrn.CheckBox "Modal , Synchronize with Central , Dialog_Revit_PartitionsSaveToMaster" _
	, "Compact Central Model (slow), Control_Revit_ForceCompactCentralModel" _
	, {compact_central}
"""

FILE_SYNC_RELEASE_BORROWED = """' Set compact central checkbox
Jrn.CheckBox "Modal , Synchronize with Central , Dialog_Revit_PartitionsSaveToMaster" _
	, "Borrowed Elements, Control_Revit_ReturnBorrowedElements" _
	, True
"""

FILE_SYNC_RELEASE_USERWORKSETS = """' Set compact central checkbox
Jrn.CheckBox "Modal , Synchronize with Central , Dialog_Revit_PartitionsSaveToMaster" _
	, "User-created Worksets, Control_Revit_RelinqUserCreatedPartitions" _
	, True
"""

FILE_SYNC_RELEASE_SAVELOCAL = """' Set compact central checkbox to
Jrn.CheckBox "Modal , Synchronize with Central , Dialog_Revit_PartitionsSaveToMaster" _
	, "Save Local File before and after synchronizing with central, Control_Revit_SavePartitionsToLocal" _
	, True
"""

FILE_SYNC_COMMENT_OK = """' Commenting and Okaying the sync dialog
Jrn.Edit "Modal , Synchronize with Central , Dialog_Revit_PartitionsSaveToMaster" _
	, "Control_Revit_Comment" _
	, "ReplaceContents" , "{sync_comment}"
Jrn.PushButton "Modal , Synchronize with Central , Dialog_Revit_PartitionsSaveToMaster" _
	, "OK, IDOK"
"""


# template for ignoring missing links
IGNORE_MISSING_LINKS = """' Ignoring missing links
Jrn.Data "TaskDialogResult"  _
    , "Revit could not find or read 1 references. What do you want to do?",  _
     "Ignore and continue opening the project", "1002"
"""


# template for exporting warnings from an open model
EXPORT_WARNINGS = """' Exporting warnings
' Jrn.RibbonEvent "TabActivated:Manage"
Jrn.Command "Ribbon" , "Review previously posted warnings , ID_REVIEW_WARNINGS"
Jrn.Data "Error dialog" , "0 failures, 0 errors, 0 warnings"
Jrn.PushButton "Modeless , Autodesk Revit Architecture 2016 , Dialog_Revit_ReviewWarningsDialog" _
          , "Export..., Control_Revit_ExportErrorReport"
Jrn.Data "Error Report Action" , "IDOK"
Jrn.Data "Error Report File Path" , "{warnings_export_path}\\"
Jrn.Data "Error Report File Name" , "{warnings_export_file}"
Jrn.Data "Error Report File Format" , "html"
Jrn.PushButton "Modeless , Autodesk Revit Architecture 2016 , Dialog_Revit_ReviewWarningsDialog" , "Close, IDABORT"
"""


# template for purging an open model
PROJECT_PURGE = """' Purge model
' Jrn.RibbonEvent "TabActivated:Manage"
Jrn.Command "Ribbon" , "Purge(delete) unused families and types, ID_PURGE_UNUSED"
Jrn.PushButton "Modal , Purge unused , Dialog_Revit_PurgeUnusedTree", "OK, IDOK"
' Jrn.Data "Transaction Successful", "Purge unused"
"""
