"""Revit-aware selection helpers using the shared modal dialogs."""

from .checks import ask_to_use_selected

from .base import DEFAULT_INPUTWINDOW_WIDTH
from .base import XAML_FILES_DIR
from .listdialog import SelectFromList
from .native import alert
from .reactive import ParamDef
from .reactive import TemplateListItem
from collections import OrderedDict
from pyrevit import DB
from pyrevit import DOCS
from pyrevit import HOST_APP
from pyrevit import coreutils
from pyrevit import framework
from pyrevit import revit
from pyrevit.compat import get_elementid_value_func
from pyrevit.coreutils import colors
from pyrevit.forms import utils
import os
import re
from pyrevit.coreutils.logger import get_logger

mlogger = get_logger(__name__)


def _make_param_def(param, istype, checked=False):
    """Build a ParamDef from a Revit parameter object."""
    if param.HasValue:
        value = param.AsValueString() or param.AsString()
        if isinstance(value, str):
            stripped_value = value.strip()
            display_value_str = value if stripped_value else None
        else:
            display_value_str = value or None
    else:
        display_value_str = None

    return ParamDef(
        name=param.Definition.Name,
        istype=istype,
        definition=param.Definition,
        isreadonly=param.IsReadOnly,
        isunit=(
            DB.UnitUtils.IsMeasurableSpec(param.Definition.GetDataType())
            if HOST_APP.is_newer_than(2022, True)
            else False
        ),
        storagetype=param.StorageType,
        displayvalue=display_value_str,
        hasvalue=display_value_str is not None,
        grouptype=(
            DB.LabelUtils.GetLabelForGroup(param.Definition.GetGroupTypeId())
            if HOST_APP.is_newer_than(2022, True)
            else DB.LabelUtils.GetLabelFor(param.Definition.ParameterGroup)
        ),
        isshared=param.IsShared,
        paramid=str(param.Id),
        checked=checked,
    )


def _get_preselect_names(preselect):
    """Return a set of names from a preselect list for item matching."""
    if not preselect:
        return set()
    names = set()
    for item in preselect:
        if isinstance(item, str):
            names.add(item)
        elif hasattr(item, "name"):
            names.add(item.name)
    return names


class RevisionOption(TemplateListItem):
    """Revision wrapper for :func:`select_revisions`."""

    def __init__(self, revision_element):
        super(RevisionOption, self).__init__(revision_element)

    @property
    def name(self):
        """Revision name (description)."""
        revnum = self.item.SequenceNumber
        rev_settings = DB.RevisionSettings.GetRevisionSettings(self.item.Document)

        if rev_settings.RevisionNumbering == DB.RevisionNumbering.PerProject:
            revnum = self.item.RevisionNumber
        return "{}-{}-{}".format(revnum, self.item.Description, self.item.RevisionDate)


class SheetOption(TemplateListItem):
    """Sheet wrapper for :func:`select_sheets`."""

    def __init__(self, sheet_element):
        super(SheetOption, self).__init__(sheet_element)

    @property
    def name(self):
        """Sheet name."""
        return "{} - {}{}".format(
            self.item.SheetNumber,
            self.item.Name,
            " (placeholder)" if self.item.IsPlaceholder else "",
        )

    @property
    def number(self):
        """Sheet number."""
        return self.item.SheetNumber


def _get_view_type_label(view):
    view_type_el = view.Document.GetElement(view.GetTypeId())
    family_name = getattr(view_type_el, "FamilyName", None)
    if family_name:
        return family_name
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", str(view.ViewType))


class ViewOption(TemplateListItem):
    """View wrapper for :func:`select_views`."""

    def __init__(self, view_element):
        super(ViewOption, self).__init__(view_element)

    @property
    def name(self):
        """View name."""
        return "{} ({})".format(
            revit.query.get_name(self.item),
            _get_view_type_label(self.item),
        )


class LevelOption(TemplateListItem):
    """Level wrapper for :func:`select_levels`."""

    def __init__(self, level_element):
        super(LevelOption, self).__init__(level_element)

    @property
    def name(self):
        """Level name."""
        return revit.query.get_name(self.item)


class FamilyParamOption(TemplateListItem):
    """Level wrapper for :func:`select_family_parameters`."""

    def __init__(
        self, fparam, builtin=False, labeled=False, associated=False, checked=False
    ):
        super(FamilyParamOption, self).__init__(fparam, checked=checked)
        self.isbuiltin = builtin
        self.islabeled = labeled
        self.isassociated = associated

    @property
    def name(self):
        """Family Parameter name."""
        return self.item.Definition.Name

    @property
    def istype(self):
        """Is type parameter."""
        return not self.item.IsInstance


def select_revisions(
    title="Select Revision",
    button_name="Select",
    width=DEFAULT_INPUTWINDOW_WIDTH,
    multiple=True,
    filterfunc=None,
    doc=None,
):
    """Standard form for selecting revisions.

    Args:
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        width (int, optional): width of list window
        multiple (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.
        doc (DB.Document, optional):
            source document for revisions; defaults to active document

    Returns:
        (list[DB.Revision]): list of selected revisions

    Examples:
        ```python
        from pyrevit import forms
        forms.select_revisions()
        [<Autodesk.Revit.DB.Revision object>,
         <Autodesk.Revit.DB.Revision object>]
        ```
    """
    doc = doc or DOCS.doc
    revisions = sorted(
        revit.query.get_revisions(doc=doc), key=lambda x: x.SequenceNumber
    )

    if filterfunc:
        revisions = filter(filterfunc, revisions)

    # ask user for revisions
    selected_revs = SelectFromList.show(
        [RevisionOption(x) for x in revisions],
        title=title,
        button_name=button_name,
        width=width,
        multiselect=multiple,
        checked_only=True,
    )

    return selected_revs


def select_sheets(
    title="Select Sheets",
    button_name="Select",
    width=DEFAULT_INPUTWINDOW_WIDTH,
    multiple=True,
    filterfunc=None,
    doc=None,
    include_placeholder=True,
    use_selection=False,
):
    """Standard form for selecting sheets.

    Sheets are grouped into sheet sets and sheet set can be selected from
    a drop down box at the top of window.

    Args:
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        width (int, optional): width of list window
        multiple (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.
        doc (DB.Document, optional):
            source document for sheets; defaults to active document
        include_placeholder (bool, optional): include a placeholder.
            Defaults to True
        use_selection (bool, optional):
            ask if user wants to use currently selected sheets.

    Returns:
        (list[DB.ViewSheet]): list of selected sheets

    Examples:
        ```python
        from pyrevit import forms
        forms.select_sheets()
        [<Autodesk.Revit.DB.ViewSheet object>,
         <Autodesk.Revit.DB.ViewSheet object>]
        ```
    """
    doc = doc or DOCS.doc

    # check for previously selected sheets
    if use_selection:
        current_selected_sheets = revit.get_selection().include(DB.ViewSheet).elements
        if filterfunc:
            current_selected_sheets = filter(filterfunc, current_selected_sheets)

        if not include_placeholder:
            current_selected_sheets = [
                x for x in current_selected_sheets if not x.IsPlaceholder
            ]

        if current_selected_sheets and ask_to_use_selected(
            "sheets", count=len(current_selected_sheets), multiple=multiple
        ):
            return current_selected_sheets if multiple else current_selected_sheets[0]

    # otherwise get all sheets and prompt for selection
    all_ops = {}
    all_sheets = (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.ViewSheet)
        .WhereElementIsNotElementType()
        .ToElements()
    )

    if filterfunc:
        all_sheets = filter(filterfunc, all_sheets)

    if not include_placeholder:
        all_sheets = [x for x in all_sheets if not x.IsPlaceholder]

    all_sheets_ops = sorted(
        [SheetOption(x) for x in all_sheets], key=lambda x: x.number
    )
    all_ops["All Sheets"] = all_sheets_ops

    sheetsets = revit.query.get_sheet_sets(doc)
    for sheetset in sheetsets:
        sheetset_sheets = [x for x in sheetset.Views if isinstance(x, DB.ViewSheet)]
        if filterfunc:
            sheetset_sheets = filter(filterfunc, sheetset_sheets)
        sheetset_ops = sorted(
            [SheetOption(x) for x in sheetset_sheets], key=lambda x: x.number
        )
        if sheetset.Name == "All Sheets":
            all_ops["[" + sheetset.Name + "]"] = sheetset_ops
        else:
            all_ops[sheetset.Name] = sheetset_ops

    # ask user for multiple sheets
    selected_sheets = SelectFromList.show(
        all_ops,
        title=title,
        group_selector_title="Sheet Sets:",
        button_name=button_name,
        width=width,
        multiselect=multiple,
        checked_only=True,
        default_group="All Sheets",
    )

    return selected_sheets


def select_views(
    title="Select Views",
    button_name="Select",
    width=DEFAULT_INPUTWINDOW_WIDTH,
    multiple=True,
    filterfunc=None,
    doc=None,
    use_selection=False,
    group_by_view_type=True,
):
    """Standard form for selecting views.

    Views are grouped by view type and the type can be selected from a
    drop down box at the top of window. Type names are localized using
    Revit's own labels.

    Args:
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        width (int, optional): width of list window
        multiple (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.
        doc (DB.Document, optional):
            source document for views; defaults to active document
        use_selection (bool, optional):
            ask if user wants to use currently selected views.
        group_by_view_type (bool, optional):
            show a view type drop down with an "All Views" entry first.
            Defaults to True

    Returns:
        (list[DB.View]): list of selected views

    Examples:
        ```python
        from pyrevit import forms
        forms.select_views()
        [<Autodesk.Revit.DB.View object>,
         <Autodesk.Revit.DB.View object>]
        ```
    """
    doc = doc or DOCS.doc

    # check for previously selected sheets
    if use_selection:
        current_selected_views = revit.get_selection().include(DB.View).elements
        if filterfunc:
            current_selected_views = filter(filterfunc, current_selected_views)

        if current_selected_views and ask_to_use_selected(
            "views", count=len(current_selected_views), multiple=multiple
        ):
            return current_selected_views if multiple else current_selected_views[0]

    # otherwise get all sheets and prompt for selection
    all_graphviews = revit.query.get_all_views(doc=doc)

    if filterfunc:
        all_graphviews = filter(filterfunc, all_graphviews)

    view_ops = sorted([ViewOption(x) for x in all_graphviews], key=lambda x: x.name)

    if group_by_view_type:
        ops_by_type = {}
        for view_op in view_ops:
            type_label = _get_view_type_label(view_op.item)
            ops_by_type.setdefault(type_label, []).append(view_op)

        all_ops = OrderedDict()
        all_ops["All Views"] = view_ops
        for type_label in sorted(ops_by_type):
            all_ops[type_label] = ops_by_type[type_label]

        return SelectFromList.show(
            all_ops,
            title=title,
            group_selector_title="View Type:",
            button_name=button_name,
            width=width,
            multiselect=multiple,
            checked_only=True,
            default_group="All Views",
            sort_groups="unsorted",
        )

    selected_views = SelectFromList.show(
        view_ops,
        title=title,
        button_name=button_name,
        width=width,
        multiselect=multiple,
        checked_only=True,
    )

    return selected_views


def select_levels(
    title="Select Levels",
    button_name="Select",
    width=DEFAULT_INPUTWINDOW_WIDTH,
    multiple=True,
    filterfunc=None,
    doc=None,
    use_selection=False,
):
    """Standard form for selecting levels.

    Args:
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        width (int, optional): width of list window
        multiple (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.
        doc (DB.Document, optional):
            source document for levels; defaults to active document
        use_selection (bool, optional):
            ask if user wants to use currently selected levels.

    Returns:
        (list[DB.Level]): list of selected levels

    Examples:
        ```python
        from pyrevit import forms
        forms.select_levels()
        [<Autodesk.Revit.DB.Level object>,
         <Autodesk.Revit.DB.Level object>]
        ```
    """
    doc = doc or DOCS.doc

    # check for previously selected sheets
    if use_selection:
        current_selected_levels = revit.get_selection().include(DB.Level).elements

        if filterfunc:
            current_selected_levels = filter(filterfunc, current_selected_levels)

        if current_selected_levels and ask_to_use_selected(
            "levels", count=len(current_selected_levels), multiple=multiple
        ):
            return current_selected_levels if multiple else current_selected_levels[0]

    all_levels = revit.query.get_elements_by_categories(
        [DB.BuiltInCategory.OST_Levels], doc=doc
    )

    if filterfunc:
        all_levels = filter(filterfunc, all_levels)

    selected_levels = SelectFromList.show(
        sorted([LevelOption(x) for x in all_levels], key=lambda x: x.Elevation),
        title=title,
        button_name=button_name,
        width=width,
        multiselect=multiple,
        checked_only=True,
    )
    return selected_levels


def select_viewtemplates(
    title="Select View Templates",
    button_name="Select",
    width=DEFAULT_INPUTWINDOW_WIDTH,
    multiple=True,
    filterfunc=None,
    doc=None,
):
    """Standard form for selecting view templates.

    Args:
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        width (int, optional): width of list window
        multiple (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.
        doc (DB.Document, optional):
            source document for views; defaults to active document

    Returns:
        (list[DB.View]): list of selected view templates

    Examples:
        ```python
        from pyrevit import forms
        forms.select_viewtemplates()
        [<Autodesk.Revit.DB.View object>,
         <Autodesk.Revit.DB.View object>]
        ```
    """
    doc = doc or DOCS.doc
    all_viewtemplates = revit.query.get_all_view_templates(doc=doc)

    if filterfunc:
        all_viewtemplates = filter(filterfunc, all_viewtemplates)

    selected_viewtemplates = SelectFromList.show(
        sorted([ViewOption(x) for x in all_viewtemplates], key=lambda x: x.name),
        title=title,
        button_name=button_name,
        width=width,
        multiselect=multiple,
        checked_only=True,
    )

    return selected_viewtemplates


def select_schedules(
    title="Select Schedules",
    button_name="Select",
    width=DEFAULT_INPUTWINDOW_WIDTH,
    multiple=True,
    filterfunc=None,
    doc=None,
):
    """Standard form for selecting schedules.

    Args:
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        width (int, optional): width of list window
        multiple (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.
        doc (DB.Document, optional):
            source document for views; defaults to active document

    Returns:
        (list[DB.ViewSchedule]): list of selected schedules

    Examples:
        ```python
        from pyrevit import forms
        forms.select_schedules()
        [<Autodesk.Revit.DB.ViewSchedule object>,
         <Autodesk.Revit.DB.ViewSchedule object>]
        ```
    """
    doc = doc or DOCS.doc
    all_schedules = revit.query.get_all_schedules(doc=doc)

    if filterfunc:
        all_schedules = filter(filterfunc, all_schedules)

    selected_schedules = SelectFromList.show(
        sorted([ViewOption(x) for x in all_schedules], key=lambda x: x.name),
        title=title,
        button_name=button_name,
        width=width,
        multiselect=multiple,
        checked_only=True,
    )

    return selected_schedules


def select_open_docs(
    title="Select Open Documents",
    button_name="OK",
    width=DEFAULT_INPUTWINDOW_WIDTH,  # pylint: disable=W0613
    multiple=True,
    check_more_than_one=True,
    filterfunc=None,
):
    """Standard form for selecting open documents.

    Args:
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        width (int, optional): width of list window
        multiple (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        check_more_than_one (bool, optional):
            Warn when fewer than two documents are open.
        filterfunc (function):
            filter function to be applied to context items.

    Returns:
        (list[DB.Document]): list of selected documents

    Examples:
        ```python
        from pyrevit import forms
        forms.select_open_docs()
        [<Autodesk.Revit.DB.Document object>,
         <Autodesk.Revit.DB.Document object>]
        ```
    """
    # find open documents other than the active doc
    open_docs = [d for d in revit.docs if not d.IsLinked]  # pylint: disable=E1101
    if check_more_than_one:
        open_docs.remove(revit.doc)  # pylint: disable=E1101

    if not open_docs:
        alert(
            "Only one active document is found. "
            "At least two documents must be open. "
            "Operation cancelled."
        )
        return

    return SelectFromList.show(
        open_docs,
        name_attr="Title",
        multiselect=multiple,
        title=title,
        button_name=button_name,
        filterfunc=filterfunc,
    )


def select_titleblocks(
    title="Select Titleblock",
    button_name="Select",
    no_tb_option="No Title Block",
    width=DEFAULT_INPUTWINDOW_WIDTH,
    multiple=False,
    filterfunc=None,
    doc=None,
):
    """Standard form for selecting a titleblock.

    Args:
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        no_tb_option (str, optional): name of option for no title block
        width (int, optional): width of list window
        multiple (bool, optional):
            allow multi-selection (uses check boxes). defaults to False
        filterfunc (function):
            filter function to be applied to context items.
        doc (DB.Document, optional):
            source document for titleblocks; defaults to active document

    Returns:
        (DB.ElementId): selected titleblock id.

    Examples:
        ```python
        from pyrevit import forms
        forms.select_titleblocks()
        <Autodesk.Revit.DB.ElementId object>
        ```
    """
    doc = doc or DOCS.doc
    titleblocks = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_TitleBlocks)
        .WhereElementIsElementType()
        .ToElements()
    )

    tblock_dict = {
        "{}: {}".format(tb.FamilyName, revit.query.get_name(tb)): tb.Id
        for tb in titleblocks
    }
    tblock_dict[no_tb_option] = DB.ElementId.InvalidElementId
    selected_titleblocks = SelectFromList.show(
        sorted(tblock_dict.keys()),
        title=title,
        button_name=button_name,
        width=width,
        multiselect=multiple,
        filterfunc=filterfunc,
    )
    if selected_titleblocks:
        if multiple:
            return [tblock_dict[x] for x in selected_titleblocks]
        else:
            return tblock_dict[selected_titleblocks]


def select_swatch(title="Select Color Swatch", button_name="Select"):
    """Standard form for selecting a color swatch.

    Args:
        title (str, optional): swatch list window title
        button_name (str, optional): swatch list window button caption

    Returns:
        (pyrevit.coreutils.colors.RGB): rgb color

    Examples:
        ```python
        from pyrevit import forms
        forms.select_swatch(title="Select Text Color")
        <RGB #CD8800>
        ```
    """
    itemplate = utils.load_ctrl_template(
        os.path.join(XAML_FILES_DIR, "SwatchContainerStyle.xaml")
    )
    swatch = SelectFromList.show(
        colors.COLORS.values(),
        title=title,
        button_name=button_name,
        width=300,
        multiselect=False,
        item_template=itemplate,
    )

    return swatch


def select_image(images, title="Select Image", button_name="Select"):
    """Standard form for selecting an image.

    Args:
        images (list[str] | list[framework.Imaging.BitmapImage]):
            list of image file paths or bitmaps
        title (str, optional): swatch list window title
        button_name (str, optional): swatch list window button caption

    Returns:
        (str): path of the selected image

    Examples:
        ```python
        from pyrevit import forms
        forms.select_image(['C:/path/to/image1.png',
                            'C:/path/to/image2.png'],
                            title="Select Variation")
        'C:/path/to/image1.png'
        ```
    """
    ptemplate = utils.load_itemspanel_template(
        os.path.join(XAML_FILES_DIR, "ImageListPanelStyle.xaml")
    )

    itemplate = utils.load_ctrl_template(
        os.path.join(XAML_FILES_DIR, "ImageListContainerStyle.xaml")
    )

    bitmap_images = {}
    for imageobj in images:
        if isinstance(imageobj, str):
            img = utils.bitmap_from_file(imageobj)
            if img:
                bitmap_images[img] = imageobj
        elif isinstance(imageobj, framework.Imaging.BitmapImage):
            bitmap_images[imageobj] = imageobj

    selected_image = SelectFromList.show(
        sorted(bitmap_images.keys(), key=lambda x: x.UriSource.AbsolutePath),
        title=title,
        button_name=button_name,
        width=500,
        multiselect=False,
        item_template=itemplate,
        items_panel_template=ptemplate,
    )

    return bitmap_images.get(selected_image, None)


def select_parameters(
    src_element,
    title="Select Parameters",
    button_name="Select",
    multiple=True,
    filterfunc=None,
    include_instance=True,
    include_type=True,
    exclude_readonly=True,
    preselect=None,
):
    """Standard form for selecting parameters from given element.

    Args:
        src_element (DB.Element): source element
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        multiple (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.
        include_instance (bool, optional): list instance parameters
        include_type (bool, optional): list type parameters
        exclude_readonly (bool, optional): only shows parameters that are editable
        preselect (list[ParamDef | str], optional):
            list of ParamDef objects or parameter name strings to pre-check

    Returns:
        (list[ParamDef]): list of paramdef objects

    Examples:
        ```python
        forms.select_parameters(
            src_element,
            title='Select Parameters',
            multiple=True,
            include_instance=True,
            include_type=True
        )
        [<ParamDef >, <ParamDef >]
        ```
    """
    preselect_names = _get_preselect_names(preselect)
    param_defs = []
    non_storage_type = coreutils.get_enum_none(DB.StorageType)
    if include_instance:
        param_defs.extend(
            [
                _make_param_def(
                    x,
                    istype=False,
                    checked=x.Definition.Name in preselect_names,
                )
                for x in src_element.Parameters
                if x.StorageType != non_storage_type
            ]
        )

    if include_type:
        src_type = revit.query.get_type(src_element) if src_element else None
        if src_type is not None:
            param_defs.extend(
                [
                    _make_param_def(
                        x,
                        istype=True,
                        checked=x.Definition.Name in preselect_names,
                    )
                    for x in src_type.Parameters
                    if x.StorageType != non_storage_type
                ]
            )

    if exclude_readonly:
        param_defs = [x for x in param_defs if not x.isreadonly]

    if filterfunc:
        param_defs = filter(filterfunc, param_defs)

    param_defs = sorted(param_defs, key=lambda x: x.name)

    itemplate = utils.load_ctrl_template(
        os.path.join(XAML_FILES_DIR, "ParameterItemStyle.xaml")
    )
    selected_params = SelectFromList.show(
        {
            "All Parameters": param_defs,
            "Instance Parameters": [x for x in param_defs if not x.istype],
            "Type Parameters": [x for x in param_defs if x.istype],
        },
        title=title,
        button_name=button_name,
        group_selector_title="Parameter Filters:",
        width=500,
        multiselect=multiple,
        item_template=itemplate,
    )

    if selected_params and isinstance(selected_params, list):
        seen = set()
        deduped = []
        for p in selected_params:
            if id(p) not in seen:
                seen.add(id(p))
                deduped.append(p)
        selected_params = deduped

    return selected_params


def select_family_parameters(
    family_doc,
    title="Select Parameters",
    button_name="Select",
    multiple=True,
    filterfunc=None,
    include_instance=True,
    include_type=True,
    include_builtin=True,
    include_labeled=True,
    include_associated=True,
    preselect=None,
):
    """Standard form for selecting parameters from given family document.

    Args:
        family_doc (DB.Document): source family document
        title (str, optional): list window title
        button_name (str, optional): list window button caption
        multiple (bool, optional):
            allow multi-selection (uses check boxes). defaults to True
        filterfunc (function):
            filter function to be applied to context items.
        include_instance (bool, optional): list instance parameters
        include_type (bool, optional): list type parameters
        include_builtin (bool, optional): list builtin parameters
        include_labeled (bool, optional): list parameters used as labels
        include_associated (bool, optional):
            list parameters associated to others
        preselect (list[FamilyParamOption | str], optional):
            list of FamilyParamOption objects or parameter name strings to pre-check

    Returns:
        (list[DB.FamilyParameter]): list of family parameter objects

    Examples:
        ```python
        forms.select_family_parameters(
            family_doc,
            title='Select Parameters',
            multiple=True,
            include_instance=True,
            include_type=True
        )
        [<FamilyParamOption >, <FamilyParamOption >]
        ```
    """
    preselect_names = _get_preselect_names(preselect)
    family_doc = family_doc or DOCS.doc
    family_params = revit.query.get_family_parameters(family_doc)
    # get all params used in labels
    label_param_ids = [
        x.Id for x in revit.query.get_family_label_parameters(family_doc)
    ]

    if filterfunc:
        family_params = filter(filterfunc, family_params)

    param_defs = []
    get_elementid_value = get_elementid_value_func()
    for family_param in family_params:
        if not include_instance and family_param.IsInstance:
            continue
        if not include_type and not family_param.IsInstance:
            continue
        if not include_builtin and get_elementid_value(family_param.Id) < 0:
            continue
        if not include_labeled and family_param.Id in label_param_ids:
            continue

        associated_to_others = not family_param.AssociatedParameters.IsEmpty
        if not include_associated and associated_to_others:
            continue

        param_defs.append(
            FamilyParamOption(
                family_param,
                builtin=get_elementid_value(family_param.Id) < 0,
                labeled=family_param.Id in label_param_ids,
                associated=associated_to_others,
                checked=family_param.Definition.Name in preselect_names,
            )
        )

    param_defs.sort(key=lambda x: x.name)

    itemplate = utils.load_ctrl_template(
        os.path.join(XAML_FILES_DIR, "FamilyParameterItemStyle.xaml")
    )
    selected_params = SelectFromList.show(
        {
            "All Parameters": param_defs,
            "Type Parameters": [x for x in param_defs if x.istype],
            "Built-in Parameters": [x for x in param_defs if x.isbuiltin],
            "Used as Label": [x for x in param_defs if x.islabeled],
            "Associated to Others": [x for x in param_defs if x.isassociated],
        },
        title=title,
        button_name=button_name,
        group_selector_title="Parameter Filters:",
        width=450,
        multiselect=multiple,
        item_template=itemplate,
    )

    if selected_params and isinstance(selected_params, list):
        seen = set()
        deduped = []
        for p in selected_params:
            if id(p) not in seen:
                seen.add(id(p))
                deduped.append(p)
        selected_params = deduped

    return selected_params
