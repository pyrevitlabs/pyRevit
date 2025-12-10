# -*- coding: utf-8 -*-
"""Advanced example showing all setting types with validation."""

from pyrevit import script
from pyrevit.forms import settings_window

my_config = script.get_config()

# Comprehensive settings with all types and validation
settings = [
    # Boolean settings
    {
        "name": "auto_save",
        "type": "bool",
        "label": "Enable Auto-Save",
        "default": True
    },
    {
        "name": "show_warnings",
        "type": "bool",
        "label": "Show Warnings",
        "default": True
    },
    
    # Choice settings (dropdown)
    {
        "name": "view_discipline",
        "type": "choice",
        "label": "View Discipline",
        "options": ["Architectural", "Structural", "Mechanical", "Electrical"],
        "default": "Architectural"
    },
    {
        "name": "detail_level",
        "type": "choice",
        "label": "Detail Level",
        "options": ["Coarse", "Medium", "Fine"],
        "default": "Medium"
    },
    
    # Integer settings with min/max validation
    {
        "name": "tolerance",
        "type": "int",
        "label": "Tolerance (mm)",
        "default": 10,
        "min": 0,
        "max": 1000
    },
    {
        "name": "grid_spacing",
        "type": "int",
        "label": "Grid Spacing",
        "default": 100,
        "min": 10,
        "max": 5000
    },
    
    # Float settings with validation
    {
        "name": "scale_factor",
        "type": "float",
        "label": "Scale Factor",
        "default": 1.0,
        "min": 0.1,
        "max": 10.0
    },
    
    # String settings
    {
        "name": "prefix",
        "type": "string",
        "label": "Element Prefix",
        "default": ""
    },
    {
        "name": "project_code",
        "type": "string",
        "label": "Project Code",
        "default": "PRJ",
        "required": True
    },
]

# Show the settings window
if settings_window.show_settings(my_config, settings, title="Advanced Tool Settings"):
    # Access saved settings
    print("Settings saved!")
    print("Auto-save: {}".format(my_config.get_option("auto_save", True)))
    print("Tolerance: {}".format(my_config.get_option("tolerance", 10)))
    print("Project Code: {}".format(my_config.get_option("project_code", "PRJ")))
else:
    print("Settings canceled")
