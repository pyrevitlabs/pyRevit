# pyRevit for Autodesk Revit®

What's pyRevit:
- It is a script `__RPS__userSetup.py` that automates the process of creating user interface for your IronPython scripts. Creating a button is as easy as adding a python script file to the pyRevit folder.

## Setup process

Setup is very easy but a few important points first:
  - This tool requires installation of most recent version of [RevitPythonShell](https://github.com/architecture-building-systems/revitpythonshell) (with `__file__` property defined)
  -  Scripts are only tested under WINDOWS OS (7,8,10) and REVIT 2015-2016.
  -  Scripts create their temporary files (e.g. the dynamic DLL module that contains the commands for each script) under user %temp% folder. But at every startup it'll cleanup after itself.

Now the setup process:
- Download and extract to your machine and place under a folder of your choice.
- Open Revit, go to RevitPythonShell > Configuration and assign `__RPS__userSetup.py` (part of this package) as the main startup script.
- Restart Revit. The `__RPS__userSetup.py` script will find all other scripts in its current directory and will create UI panels and buttons under 'pyRevit' ribbon tab. See below on how to add our own scripts and shortcuts to this tool.

## How to add your scripts:

The `__RPS__userSetup.py` startup script will setup a ribbon panel named 'pyRevit'. There are 5 ways to add buttons to this ribbon panel and categorize them under sub-panels.

####Method 1 (PullDown Buttons):
Step 1: Create a `.png` file, with name pattern as below:

`<00 Panel Order><00 Button Order>_<Panel Name>_PulldownButton_<Button Group Name>.png`

Example:

`1003_Selection_PulldownButton_Filter.png` defines a subpanel under `pyRevit` ribbon panel, named `Selection`, with order number `10`, and a `PulldownButton` in this panel, named `Filter` with order number `03`. Startup script will use the order numbers to sort the panels and buttons and later to create them in order. 

Step 2: All `.py` script under the home directory should have the below name pattern:

`<Button Group Name>_<Script Command Name>.py`

Scripts be organized under the group button specified in the source file name. For example a script file named `Filter_filterGroupedElements.py` will be placed under group button `Filter` (defined by the `.png` above) and its command name will be `filterGroupedElements`. The `.png` file defining the Pulldown Button will be used as the default icon.

####Method 2 (SplitButton):
Same as Method 1 except it will create Split Buttons (The last selected sub-item will be the default active item)

For the Method 1 and 2 scripts, if there is a `.png` file with a matching name to a script, that `.png` file will override the default image and will be used as the button icon.

Example:
`Analyse_sumAllSelectedEntityVolumes.png`
`Analyse_sumAllSelectedEntityVolumes.py`
This `.png` image will override the default icon for Analyse group button.

####Method 3 (Stack3):
Step 1: Create a `.png` file, with name pattern as below:

`<00 Panel Order><00 Button Order>_<Panel Name>_Stack3_<Stack Name>.png`

Example:

`1005_Selection_Stack3_Inspect.png` defines a subpanel under `pyRevit`, named `Selection`, with order number `10`, and 3 Stacked Buttons in this panel, named `Inspect` with order number `05`. Startup script will use the order numbers to sort the panels and buttons and later to create them in order. For a Stack3 button group, the startup script will expect to find exactly 3 scripts to be categorized under this stack. The actual stack name will be ignored since the stack doesn't have any visual representation other then the 3 buttons stacked in 3 rows. The scripts use the same naming pattern as Method 1. As an example the 3 scripts below will be used to create 3 buttons in this stack (sorted alphabetically):

`Inspect_findLinkedElements.py`
`Inspect_findListOfViewsShowingElement.py`
`Inspect_findPaintedSurfacesOnSelected.py`

####Method 4 (PushButton):
Step 1: Create a `.png` file, with name pattern as below:

`<00 Panel Order><00 Button Order>_<Panel Name>_PushButton_<Button Name>.png`

Example:

`1005_Revit_PushButton_BIM.png` defines a subpanel under `pyRevit`, named `Revit`, with order number `10`, and a simple Push Buttons in this panel, named `BIM` with order number `05`. Startup script will use the order numbers to sort the panels and buttons and later to create them in order. The startup script will expect to find only one script with name pattern similar to Method 1, and will assign it to this push button.

Example:
`BIM_getCentralPath.py` will be assigned to the push button described above. The button name will be `getCentralPath`.


####Method 5 (Link Buttons):
This button creates a link to another command of any other addin.

Step 1: Create a `.png` file, with name pattern as below:

`<00 Panel Order><00 Button Order>_<Panel Name>_PushButton_<Button Name>_<Assembly Name>_<C# Class Name>.png`

Example:

`0000_RPS_PushButton_RPS_RevitPythonShell_IronPythonConsoleCommand.png` defines a subpanel under `pyRevit`, named `RPS`, with order number `00`, and a simple Push Buttons in this panel, named `RPS` with order number `00`. But then the startup script will use the assembly name and class name and will assign them to the button. In this example, startup script will create a button that opens the 'Interactive Python Shell' from RevitPythonShell addin. Another example of this method is `0005_RL_PushButton_Lookup_RevitLookup_CmdSnoopDb.png` that will create a button calling the 'Snoop DB' command of the RevitLookup addin. This type of button does not need any external scripts. This single `.png` file has all the necessary information for this link button.

I hope I have explained everything clearly and you find it simple to use.

If you added scripts or panels while Revit is running, use the `reloadScripts` button from the `Settings` group to reload the changes. It'll search for the scripts and will update the buttons, disabling the missing and adding the newly found.

## Documentation:

I'll figure out a system for the documentation soon ([ReadTheDocs](https://readthedocs.org/) seems to be a good option). But for now please refer to tooltips for every script button. The text for the tooltips are included inside each script source file, defined as `__doc__` parameter.
I'm open to comments and suggestions :)

#### Versioning:
I'm using semantic versioning with MAJOR.MINOR.PATCH format:

  MAJOR: incompatible API changes
  
  MINOR: add functionality and scripts in a backwards-compatible manner
  
  PATCH: backwards-compatible bug fixes

## Contribute

- Issue Tracker: https://github.com/eirannejad/pyRevit/issues
- Source Code: https://github.com/eirannejad/pyRevit

And please feel free to fork, modify and add your own scripts, and send me pull requests. I'd be thrilled to add more tools and scripts to this for everyone to use.

## Support

[stackoverflow](http://stackoverflow.com) (Note: use `pyRevit` tag)

## License

This package is licensed under  GNU GENERAL PUBLIC LICENSE, Version 3, 29 June 2007.
See LICENSE.md for full license text.
See [this](http://choosealicense.com/) page for more help on licensing your work.

## Credits

I'd like to thank people listed here for their great contributions:
  * [Daren Thomas](https://github.com/daren-thomas) (original version, maintainer of [RevitPythonShell](https://github.com/architecture-building-systems/revitpythonshell)) for creating RPS that this package is heavily relying on and helping me through out this process.
  * [Jeremy Tammik](https://github.com/jeremytammik) (creator and maintainer of [RevitLookup](https://github.com/jeremytammik/RevitLookup))
  * [Icons8](https://icons8.com/) for the beautiful icons.
  * [ThubanPDX](https://github.com/ThubanPDX). Testing and new ideas for tools and scripts.

**NOTE**: If you are not on this list, but believe you should be, please contact me!
