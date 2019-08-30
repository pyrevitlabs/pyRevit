from pyrevit import DB, revit

def get_view(element, allow_active_view=False):
    """
    Tries to get a view from selected elements (Viewport, View)
    or get an active view (if allow_active_view is True)
    :param element: element to extract view from (Viewport, View)
    :param allow_active_view: take active view if element is not a view
    :return: DB.View element
    """
    view = None
    # try to get view of selected viewport
    if isinstance(element, DB.Viewport):
        view = element.Document.GetElement(element.ViewId)
    # get selected views, e.g. from ProjectBrowser
    if isinstance(element, DB.View) and not view:
        view = element
    if not view and allow_active_view:
        view = revit.activeview
    return view

def get_viewport(element, allow_active_view=False):
    """
    Tries to get a viewport from selected elements (Viewport, View)
    or get a viewport from an active view (if allow_active_view is True)
    :param element: element to extract viewport from (Viewport, View)
    :param allow_active_view: take viewport of active view
    :return: DB.Viewport element
    """
    viewport = None
    # try to get viewport of selected view
    if isinstance(element, DB.View):
        viewport = get_viewport_by_view(element)
    # get selected viewports
    if isinstance(element, DB.Viewport) and not viewport:
        viewport = element
    # get current view viewport
    if not viewport and allow_active_view:
        viewport = get_viewport_by_view(revit.activeview)
    return viewport


def get_views(elements):
    result = []
    for e in elements:
        result.append(get_view(e))
    if not result:
        result = [revit.activeview]
    return result


def get_viewports(elements):
    result = []
    for e in elements:
        result.append(get_viewport(e))
    if not result:
        result = [get_viewport_by_view(revit.activeview)]
    return result


def get_viewport_by_view(view):
    sheet = get_view_sheet(view)
    if not sheet:
        return
    cl = DB.FilteredElementCollector(view.Document)\
        .WhereElementIsNotElementType().OfClass(DB.Viewport)
    viewports = list(filter(lambda v: v.ViewId == view.Id, cl.ToElements()))
    if len(viewports) == 0:
        return
    return viewports[0]

def get_view_sheet(view):
    sheet_num_param = view.get_Parameter(
        DB.BuiltInParameter.VIEWPORT_SHEET_NUMBER)
    if not sheet_num_param:
        return None
    sheet_num = sheet_num_param.AsString()
    cl = DB.FilteredElementCollector(view.Document)\
        .WhereElementIsNotElementType().OfClass(DB.ViewSheet)
    sheets = list(filter(lambda s: s.SheetNumber == sheet_num, cl.ToElements()))
    if len(sheets) == 0:
        return
    return sheets[0]