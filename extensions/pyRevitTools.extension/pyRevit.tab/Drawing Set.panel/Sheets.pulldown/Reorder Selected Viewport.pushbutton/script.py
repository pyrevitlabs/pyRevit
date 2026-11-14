# -*- coding: utf-8 -*-
"""Reorders the selected viewport on current sheet."""

from collections import namedtuple

from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import HOST_APP
from pyrevit.coreutils import applocales


RESOURCES = {
    "reordering_methods": {
        "en_us": ("Bring to Front", "Send to Back"),
        "fr_fr": ("Mettre au premier plan", "Mettre à l'arrière-plan"),
        "ru": ("На передний план", "На задний план"),
        "chinese_s": ("置于顶层", "置于底层"),
        "ko": ("맨 앞으로 가져오기", "맨 뒤로 보내기"),
        "es_es": ("Traer al frente", "Enviar al fondo"),
        "de_de": ("In den Vordergrund", "In den Hintergrund"),
        "pt_br": ("Trazer para frente", "Enviar para trás"),
    },
    "reordering_methods_message": {
        "en_us": "Select reordering method:",
        "fr_fr": "Sélectionnez la méthode de réorganisation :",
        "ru": "Выберите способ изменения порядка:",
        "chinese_s": "选择重新排序方式：",
        "ko": "재정렬 방법을 선택하세요:",
        "es_es": "Seleccione el método de reordenación:",
        "de_de": "Sortiermethode auswählen:",
        "pt_br": "Selecione o método de reordenação:",
    },
    "no_viewport_selected": {
        "en_us": "Select a Viewport first.",
        "fr_fr": "Sélectionnez d'abord une fenêtre de vue.",
        "ru": "Сначала выберите видовой экран.",
        "chinese_s": "请先选择一个视口。",
        "ko": "먼저 뷰포트를 선택하세요.",
        "es_es": "Seleccione primero una ventana gráfica.",
        "de_de": "Bitte zuerst einen Ansichtsfensterbereich auswählen.",
        "pt_br": "Selecione primeiro uma viewport.",
    },
}


ViewportConfig = namedtuple(
    "ViewportConfig",
    [
        "box_center",
        "type_id",
        "view_id",
        "rotation",
        "label_offset",
        "label_line_length",
    ]
)


def _ls(key):
    return applocales.get_locale_string(RESOURCES[key])


def get_selected_viewports():
    selection = revit.get_selection()
    return [x for x in selection if isinstance(x, DB.Viewport)]


def get_nonselected_viewports(sheet):
    svps = get_selected_viewports()
    svp_ids = [x.Id for x in svps]
    if isinstance(sheet, DB.ViewSheet):
        vps = sheet.GetAllViewports()
        if svp_ids:
            return [revit.doc.GetElement(x) for x in vps if x not in svp_ids]

    return []


def capture_vp_config(viewport):
    is_newer = HOST_APP.is_newer_than(2021)

    return ViewportConfig(
        viewport.GetBoxCenter(),
        viewport.GetTypeId(),
        viewport.ViewId,
        viewport.Rotation,
        viewport.LabelOffset if is_newer else None,
        viewport.LabelLineLength if is_newer else None,
    )


def bring_to_front(sheet, vp_list):
    with revit.Transaction("Reorder Viewports"):
        for vp in vp_list:
            config = capture_vp_config(vp)
            sheet.DeleteViewport(vp)
            new_vp = DB.Viewport.Create(
                revit.doc, sheet.Id, config.view_id, config.box_center
            )
            new_vp.ChangeTypeId(config.type_id)
            new_vp.Rotation = config.rotation
            new_vp.SetBoxCenter(config.box_center)
            if HOST_APP.is_newer_than(2021):
                new_vp.LabelOffset = config.label_offset
                new_vp.LabelLineLength = config.label_line_length


selected_vps = get_selected_viewports()

front_mode, back_mode = _ls("reordering_methods")

if selected_vps:
    selected_option = forms.CommandSwitchWindow.show(
        [front_mode, back_mode], message=_ls("reordering_methods_message")
    )

    if selected_option:
        if selected_option == front_mode:
            viewports = selected_vps
        elif selected_option == back_mode:
            viewports = get_nonselected_viewports(revit.active_view)

        bring_to_front(revit.active_view, viewports)
else:
    forms.alert(_ls("no_viewport_selected"))
