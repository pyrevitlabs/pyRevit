# -*- coding: utf-8 -*-
# pylint: disable=import-error,invalid-name,attribute-defined-outside-init,broad-except
"""Copies the state of desired parameter of the active
view to memory. e.g. Visibility Graphics settings or
Zoom state. Run it and see how it works.
"""

from pyrevit import PyRevitException
from pyrevit import forms
from pyrevit.coreutils import applocales

import copypastestate


RESOURCES = {
    "selected_action_message": {
        "en_us": "Select property to be copied to memory:",
        "fr_fr": "Sélectionnez la propriété à copier en mémoire:",
        "ru": "Выберите параметр для копирования в память:",
        "chinese_s": "选择要复制到内存的属性:",
        "ko": "메모리에 복사할 속성을 선택하세요.",
        "es_es": "Seleccione la propiedad que desea copiar a la memoria:",
        "de_de": "Eigenschaft auswählen, die in den Speicher kopiert werden soll:",
        "pt_br": "Selecione a propriedade a ser copiada para a memória:",
    },
}

# collect actions that are valid in this context
available_actions = [x for x in copypastestate.get_actions() if x.validate_context()]

if available_actions:
    action_options = {x.name: x for x in available_actions}
    selected_action = forms.CommandSwitchWindow.show(
        action_options.keys(),
        message=applocales.get_locale_string(RESOURCES["selected_action_message"]),
        name_attr="name",
    )

    if selected_action:
        action = action_options[selected_action]
        try:
            action().copy()
        except PyRevitException as ex:
            forms.alert(ex.msg)
