"""Testing toast64 module."""
from pyrevit import forms

forms.toast(
    "Hello World!",
    title="My Script",
    appid="MyAPP",
    click="https://eirannejad.github.io/pyRevit/",
    actions={
        "Open Google":"https://google.com",
        "Open Toast64":"https://github.com/go-toast/toast"
        })
