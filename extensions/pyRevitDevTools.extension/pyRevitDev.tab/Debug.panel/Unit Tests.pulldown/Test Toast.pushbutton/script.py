# -*- coding: utf-8 -*-
"""Testing toast64 module."""
from pyrevit import forms

forms.toast(
    "🚀 PyRevit Rocks!",
    title="My Script",
    click="https://www.pyrevitlabs.io",
    actions={
        "Donate": "https://opencollective.com/pyrevitlabs/donate", 
        "Docs": "https://docs.pyrevitlabs.io/"
    }
)
