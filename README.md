# pyRevit for Autodesk Revit®

##What is pyRevit:

- In it's simplest form, it's a folder filled with `.py` IronPython scripts for Revit.
- There is also an IronPython script `__init__.py` that creates UI buttons for your IronPython scripts at Revit startup. Creating a button is as easy as adding a python script file to the pyRevit folder and reloading pyRevit. See below on how to add your scripts.

## Installation:
[**SETUP PACKAGE**](https://github.com/eirannejad/pyRevit/releases/download/Setup/pyRevitPackage.zip)

- Download the setup package, extract to your machine and place under a folder of your choice.
- Run `Setup.bat` and all scripts will be downloaded to this folder.
- Setup script will create the necessary `.addin` file for Revit 2015 and 2016 to load the scripts at Revit startup.
- Run Revit and pyRevit will automatically load.

This package installs a tiny addon on your Revit that its sole purpose in life is to run the `__init__.py` at Revit startup. This addon is named RevitPythonLoader and is a fork of RevitPythonShell. How does it find the `__init__.py` you ask? Through a windows environment variable called `%pyRevit%` that it also automatically creates at installation. This variable points to the folder containing the `__init__.py` file.

**About Versioning:** I'm using semantic versioning with MAJOR.MINOR.PATCH format. (MAJOR: incompatible API changes, MINOR: add functionality and scripts in a backwards-compatible manner, PATCH: backwards-compatible bug fixes). You can see your pyRevit version under `Settings -> aboutPyRevit`

## Using the scripts:
After you installed pyRevit and launched Revit, the startup script will find all the individual scripts and creates the UI buttons for the commands.

Just click on the pyRevit tab and click on the command you'd like run. Most command names are self-explanatory but there is a tooltip on the more complicated commands that describes the function. This tooltip is created from `__doc__` string inside each `.py` file.

## Adding your own scripts:

The `__init__.py` startup script will setup a ribbon panel named 'pyRevit' (After the folder name that contains the scripts). There are 5 ways to add buttons to this ribbon panel and categorize them under sub-panels.

####All the methods listed below, require a 32x32 pixel `.png` image file that will be used as the icon for the button or button group.

####Method 1 (PullDown Buttons):

- Step 1: Create a `.png` file, with this naming pattern:
`<00 Panel Order><00 Button Order>_<Panel Name>_PulldownButton_<Button Group Name>.png`
  
  Example:  
  `1003_Selection_PulldownButton_Filter.png`  
  This `.png` file, defines a subpanel under `pyRevit` ribbon panel named `Selection`, and a `PulldownButton` named `Filter` under this panel. Startup script will use the order numbers to sort the panels and buttons and later to create them in order.

- Step 2: All `.py` script under the home directory should have the below name pattern:
`<Button Group Name>_<Script Command Name>.py`

Scripts be organized under the group button specified in the source file name. For example a script file named `Filter_filterGroupedElements.py` will be placed under group button `Filter` (defined by the `.png` above) and its command name will be `filterGroupedElements`. The `.png` file defining the Pulldown Button will be used as button icon by default, however, if there is a `.png` file with a matching name to a script, that `.png` file will override the default image and will be used as the button icon.

####Method 2 (SplitButton):
Same as Method 1 except it will create Split Buttons (The last selected sub-item will be the default active item)

####Method 3 (Stack3):
Create a `.png` file, with this naming pattern:
`<00 Panel Order><00 Button Order>_<Panel Name>_Stack3_<Stack Name>.png`

Example:  
`1005_Selection_Stack3_Inspect.png` defines a subpanel under `pyRevit`named `Selection`, and 3 Stacked Buttons in this panel. For a Stack3 button group, the startup script will expect to find exactly 3 scripts to be categorized under this stack. The actual stack name will be ignored since the stack doesn't have any visual representation other then the 3 buttons stacked in 3 rows.
In this example the 3 scripts below will be used to create 3 buttons in this stack (sorted alphabetically):

`Inspect_findLinkedElements.py`
`Inspect_findListOfViewsShowingElement.py`
`Inspect_findPaintedSurfacesOnSelected.py`

Notice that the scripts use the same naming pattern as Method 1.  

####Method 4 (PushButton):
Create a `.png` file, with this naming pattern:
`<00 Panel Order><00 Button Order>_<Panel Name>_PushButton_<Button Name>.png`

Example:

`1005_Revit_PushButton_BIM.png` defines a subpanel under `pyRevit` named `Revit`, and a simple Push Buttons in this panel named `BIM`. The startup script will expect to find only one script with name pattern similar to Method 1, and will assign it to this push button.

Example:
`BIM_getCentralPath.py` will be assigned to the push button described above. The button name will be `getCentralPath`.


####Method 5 (Link Buttons):
This button creates a link to another command of any other addin. Create a `.png` file, with the same naming pattern as Method 1, but also add `<Assembly Name>` and `<C# Class Name>` to the filename separated by `_`.

Example:  
`0000_RPS_PushButton_RPS_RevitPythonShell_IronPythonConsoleCommand.png`

This defines a subpanel under `pyRevit`, named `RPS`, and a simple Push Buttons in this panel, named `RPS`. But then the startup script will use the assembly name and class name and will assign them to the button. In this example, startup script will create a button that opens the 'Interactive Python Shell' from RevitPythonShell addin.

Another example of this method is `0005_RL_PushButton_Lookup_RevitLookup_CmdSnoopDb.png` that will create a button calling the 'Snoop DB' command of the RevitLookup addin. This type of button does not need any external scripts. This single `.png` file has all the necessary information for this link button.

## Reloading the scripts library:
pyRevit commands only keep a link to the actual IronPython script file. Revit reads and runs the script file any time the user clicks on the corresponding button. This means you can edit any script while Revit is running and the next time you click on the corresponding script button, Revit will run the modifed script file.

If you added scripts or panels while Revit is running, use the `reloadScripts` button from the `Settings` group to reload the changes. It'll search for the scripts and will update the buttons, disabling the missing and adding the newly found.

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

- [Daren Thomas](https://github.com/daren-thomas) (original version, maintainer of [RevitPythonShell](https://github.com/architecture-building-systems/revitpythonshell)) for creating RPS and helping me.
- [Jeremy Tammik](https://github.com/jeremytammik) (creator and maintainer of [RevitLookup](https://github.com/jeremytammik/RevitLookup))
- [Icons8](https://icons8.com/) for the beautiful icons.
- [ThubanPDX](https://github.com/ThubanPDX). For testing and new ideas for tools and scripts.

**NOTE**: If you are not on this list, but believe you should be, please contact me!
