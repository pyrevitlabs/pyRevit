# -*- coding: utf-8 -*-
# pylint: disable=import-error,invalid-name,attribute-defined-outside-init
"""Applies the copied state to the active view.
This works in conjunction with the Copy State tool.

Shift-Click:
Show additional options
"""

from pyrevit import PyRevitException
from pyrevit import forms, script
from pyrevit.coreutils import applocales

import copypastestate


RESOURCES = {
    "selected_action_message": {
        "en_us": "Select property to be pasted:",
        "fr_fr": "Sélectionnez la propriété à coller",
        "ru": "Выберите параметр для вставки",
        "chinese_s": "选择要粘贴的属性",
        "es_es": "Seleccione la propiedad que desea pegar",
        "de_de": "Eigenschaft zum Einfügen auswählen",
        "pt_br": "Selecione a propriedade a ser colada",
    },
    "available_actions_none": {
        "en_us": 'No available actions for this view or no saved data found. Use "Copy State" first.',
        "fr_fr": (
            "Aucune action disponible pour cette vue ou aucune donnée enregistrée trouvée."
            'Utilisez d’abord \"Copier l\'état\".'
        ),
        "ru": (
            "Для этого вида нет доступных действий или не найдены сохранённые данные."
            'Сначала используйте "Копировать".'
        ),
        "chinese_s": '此视图没有可用的操作，或未找到已保存的数据。请先使用 "复制状态"',
        "es_es": (
            "No hay acciones disponibles para esta vista o no se encontraron datos guardados."
            'Utilice primero "Copiar estado".'
        ),
        "de_de": (
            "Für diese Ansicht sind keine Aktionen verfügbar oder es wurden keine gespeicherten Daten gefunden."
            'Verwenden Sie zuerst "Zustand kopieren".'
        ),
        "pt_br": (
            "Não há ações disponíveis para esta vista ou nenhum dado salvo foi encontrado."
            'Use primeiro "Copiar Estado".'
        ),
    },
}


def _ls(key):
    return applocales.get_locale_string(RESOURCES[key])


# collect actions that are valid in this context
available_actions = [
    x
    for x in copypastestate.get_actions()
    if x.validate_context()
    and script.data_exists(x.__name__, this_project=x.this_project)
]

if available_actions:
    if len(available_actions) > 1:
        action_options = {x.name: x for x in available_actions}
        selected_action = forms.CommandSwitchWindow.show(
            action_options.keys(),
            message=_ls("selected_action_message"),
            name_attr="name",
        )
        if selected_action:
            action = action_options[selected_action]
        else:
            script.exit()
    else:
        action = available_actions[0]

    try:
        action().paste()
    except PyRevitException as ex:
        forms.alert(ex.msg)
else:
    forms.alert(
        _ls("available_actions_none")
    )
