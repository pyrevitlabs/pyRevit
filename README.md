# pyRevit for Autodesk Revit®

##What is pyRevit:

- In it's simplest form, it's a folder of IronPython `.py` scripts for Autodesk Revit.
- There is also an IronPython helper script, named `__init__.py`, that creates a ribbon tab and creates UI buttons for the IronPython scripts at Revit startup. Adding a button to this tab is as easy as adding a IronPython script file to the pyRevit folder and reloading pyRevit. 


Follow the instructions below on how to add your own scripts.

## Installation (Using the installer):

[![package](http://eirannejad.github.io/pyRevit/images/Software%20Box-48.png)  
**DOWNLOAD SETUP PACKAGE**](https://github.com/eirannejad/pyRevit/releases/download/Setup/pyRevitPackage.zip)

- Download the setup package, extract to your machine.
- Run `Setup.bat` and all scripts will be downloaded to this folder.
- Setup script will create the necessary `.addin` file for Revit 2015 and 2016 to load the scripts at Revit startup.
- Run Revit and a `pyRevit` tab will be added to the Revit ribbon.

This package adds an addin on your Revit that its sole purpose is to run the `__init__.py` at Revit startup. This addin is named [RevitPythonLoader](https://github.com/eirannejad/revitpythonloader) and is a fork of [RevitPythonShell](https://github.com/architecture-building-systems/revitpythonshell).

How does it find the `__init__.py` you ask? Through a windows environment variable named `%pyRevit%` that it also automatically created by `Setup.bat` at installation. This variable points to the folder containing the `__init__.py` file which is t he downloaded pyRevit library. This folder can be a local folder or a nework folder (e.g `%pyRevit% = //Server/BIM/Revit/pyRevit/` 

Neil Reilly has prepared a handy video taking you through the installation and showing some of the more useful tools. Click here to go to his Youtube page and watch the video.

[![NeilReillyVideo](http://eirannejad.github.io/pyRevit/images/neilreillyvideo1.jpg)](https://www.youtube.com/watch?v=71rvCspWNHs)

**If you encountered any errors during the installation, please use the manual installation method described below:**

## Installation (Manual installation):

This method needs basic knowledge of cloning/downloading git repositories:

- Clone/Download the pyRevit repository onto your machine.

**If you DO have [RevitPythonShell](https://github.com/architecture-building-systems/revitpythonshell) installed on your Revit:**

- Go to `RevitPythonShell` Configuration, under the `InitScript \ Startup Script` tab, click on the browse button for the Startup Script and browse to `__init__.py` in the cloned pyRevit folder.
- Restart your Revit and `RevitPythonShell` will load the `__init__.py` script and a `pyRevit` tab will be added to the ribbon panel.

**If you DO NOT have [RevitPythonShell](https://github.com/architecture-building-systems/revitpythonshell) installed on your Revit:**

- Clone/Download the [RevitPythonLoader](https://github.com/eirannejad/revitpythonloader) repository onto your machine.
- Create an environment variable named `%pyrevit%` on your machine and assign the location of `__init__.py` script to this variable (e.g. `%pyrevit% = "C:\pyrevit\"`
- Download this [template add-in file](http://eirannejad.github.io/pyRevit/misc/RevitPythonLoader.addin) and add it to your Revit addin folder (usually: `appdata%\Autodesk\Revit\Addins\2016` for Revit 2016)
- Edit the downloaded addin file with a text editor and replace the `<RPL_repo_location>` with the folder address of the cloned `RevitPythonLoader` repository.
- Start Revit. Revit will find `RevitPythonLoader` with the help of the `addin` file, and RevitPythonLoader will read the value of `%pyrevit%` and will load the `__init__.py` script. A `pyRevit` tab will be added to the ribbon panel.


**About Versioning:** I'm using semantic versioning with MAJOR.MINOR.PATCH format. (MAJOR: incompatible API changes, MINOR: add functionality and scripts in a backwards-compatible manner, PATCH: backwards-compatible bug fixes). You can see your pyRevit version under `Settings -> aboutPyRevit`

## Using the scripts:
After you installed pyRevit and launched Revit, the startup script will find all the individual scripts and creates the UI buttons for the commands.

Just click on the pyRevit tab and click on the command you'd like run. Most command names are self-explanatory but there is a tooltip on the more complicated commands that describes the function. This tooltip is created from `__doc__` string inside each `.py` file.

## Adding your own scripts:

The `__init__.py` startup script will setup a ribbon panel named 'pyRevit' (After the folder name that contains the scripts). There are 5 ways to add buttons to this ribbon panel and categorize them under sub-panels.

####All the methods listed below, require a 32x32 pixel `.png` image file that will be used as the icon for the button or button group. If you're creating your own icons, in Photoshop, just use Save For Web, Legacy PNG-8. Otherwise the icon might be displayed larger than expected.

***
###Creating Pull Down Buttons:
![PulldownDemo](http://eirannejad.github.io/pyRevit/images/pulldownbuttondemo.png)  

- **Step 1:** Create a `.png` file, with this naming pattern:
`<00 Panel Order><00 Button Order>_<Panel Name>_PulldownButton_<Button Group Name>.png`
  
  **Example:**  
  `1003_Selection_PulldownButton_Filter.png`  
  This `.png` file, defines a sub-panel under `pyRevit` ribbon panel named `Selection`, and a `PulldownButton` named `Filter` under this panel. Startup script will use the order numbers to sort the panels and buttons and later to create them in order.

- **Step 2:** All `.py` script under the home directory should have the below name pattern:
`<Button Group Name>_<Script Command Name>.py`.  
For the example above, any script that its name starts with `Filter_` will be added to this PullDown button.

Scripts will be organized under the group button specified in the source file name. For example a script file named `Filter_filterGroupedElements.py` will be placed under group button `Filter` (defined by the `.png` above) and its command name will be `filterGroupedElements`. The `.png` file defining the Pulldown Button will be used as button icon by default, however, if there is a `.png` file with a matching name to a script, that `.png` file will override the default image and will be used as the button icon.

###Split Buttons: Creating Pull Down buttons that remember the last clicked button
Same as Method 1 except it will create Split Buttons (The last selected sub-item will be the default active item).

For a SplitButton, create a `.png` file, with this naming pattern:
`<00 Panel Order><00 Button Order>_<Panel Name>_SplitButton_<Button Group Name>.png`

![SplitDemo](http://eirannejad.github.io/pyRevit/images/splitbuttondemo.png)  

***
###Creating Push Buttons:  
![PushbuttonDemo](http://eirannejad.github.io/pyRevit/images/pushbuttondemo.png)  

- **Step 1:** Create a `.png` file, with this naming pattern:
`<00 Panel Order><00 Button Order>_<Panel Name>_PushButton_<Push Button Name>.png`

	**Example:**  
	`1005_Revit_PushButton_Get Central Path.png` defines a sub-panel under `pyRevit` named `Revit`, and a simple Push Buttons in this panel named `BIM`. The startup script will expect to find only one script with name pattern similar to Method 1, and will assign it to this push button.

- **Step 2:** All `.py` script under the home directory should have the below name pattern:
`<Push Button Name>_<Script Name>.py`.  
For the example above, `Get Central Path_action.py` will be assigned to the push button described above. Not that the The button name shown in the ribbon will be `Get Central Path` (`<Push Button Name>`) since this button only performs one action. The `<Script Name>` will be ignored.

####Link Buttons: Creating Push Buttons that Run other Addin's Commands
This button is very similar to a PushButton except that it creates a link to a command of any other addin.  
Create a `.png` file, with the same naming pattern as Method 1, but also add `<Assembly Name>` and `<C# Class Name>` to the filename separated by `_`.

**Example:**  
`0000_RPS_PushButton_RPS_RevitPythonShell_IronPythonConsoleCommand.png`

This defines a sub-panel under `pyRevit`, named `RPS`, and a simple Push Buttons in this panel, named `RPS`. But then the startup script will use the `<Assembly Name>` and `<C# Class Name>` and will look for the referenced addin and class. If this addin has been already loaded into Revit, the startup script will assign the `<C# Class Name>` to this button. In this example, startup script will create a button that opens the 'Interactive Python Shell' from RevitPythonShell addin.

Another example of this method is `0005_RL_PushButton_Lookup_RevitLookup_CmdSnoopDb.png` that will create a button calling the 'Snoop DB' command of the [RevitLookup](https://github.com/jeremytammik/RevitLookup) addin.

Notice that this type of button does not need any external scripts. This single `.png` file has all the necessary information for this link button.

***
###Creating Stack of Push Buttons:
![Stack3Demo](http://eirannejad.github.io/pyRevit/images/stackthreedemo.png)

- **Step 1:** Create a `.png` file, with this naming pattern:
`<00 Panel Order><00 Button Order>_<Panel Name>_Stack3_<Stack Name>.png`  

	**Example:**  
	`1005_Selection_Stack3_Inspect.png` defines a sub-panel under `pyRevit`named `Selection`, and 3 Stacked Buttons in this panel. For a Stack3 button group, the startup script will expect to find exactly 3 scripts to be categorized under this stack. The actual stack name will be ignored since the stack doesn't have any visual representation other then the 3 buttons stacked in 3 rows.

- **Step 2:** All `.py` script under the home directory should have the below name pattern:
`<Button Group Name>_<Script Command Name>.py`.  
In this example the 3 scripts below will be used to create 3 buttons in this stack (sorted alphabetically):

	`Inspect_findLinkedElements.py`  
	`Inspect_findListOfViewsShowingElement.py`  
	`Inspect_findPaintedSurfacesOnSelected.py`  

## Adding your own tabs:
By default, the `__init__.py` script will load all the scripts inside the `pyRevit` folder provided in this repository. But the `__init__.py` script, will also look for other folders in its directory. This means that you can create other folders alongside the `__init__.py` and `pyRevit` and place your custom scripts under those. The `__init__.py` script will create a dedicated tab (with the folder name) for each of the folders that contains scripts, in Revit ribbon after `pyRevit` tab.

This is the preferred method for adding your custom scripts and categories to the pyRevit library. This way, the original pyRevit library can remain intact and always be updated from the github repository to the latest version.

## Reloading the scripts library:
![ReloadScripts](http://eirannejad.github.io/pyRevit/images/reloadScripts.png)

pyRevit commands only keep a link to the actual IronPython script file. Revit reads and runs the script file any time the user clicks on the corresponding button. This means you can edit any script while Revit is running and the next time you click on the corresponding script button, Revit will run the modified script file.

If you added scripts or panels while Revit is running, use the `reloadScripts` button from the `Settings` group to reload the changes. It'll search for the scripts and will update the buttons, disabling the missing and adding the newly found.

## Keeping your library up to date:
Use the `downloadUpdates` button under the `Settings` pull down to fetch all the recent changes from the github repository.

![DownloadUpdates](http://eirannejad.github.io/pyRevit/images/downloadUpdates.png)

**pyRevit** will open a window and will fetch the most recent changes from the github repository. Keep in mind that the changes you have made to the original scripts included in the library will be overwritten. Any extra scripts and file will remain intact. After the update, click on Reload Scripts to get buttons for any newly added script.

![FetchingUpdates](http://eirannejad.github.io/pyRevit/images/fetchingupdates.png)


## Reinstall / Uninstall:
Run `Setup.bat` and it'll prompt you that the pyRevit or RevitPythonLoader folders already exist and if you want to Reinstall pyRevit. If you answer yes, it'll delete the folders and re-clones the github repositories just like a fresh install.
 
![Reinstall](http://eirannejad.github.io/pyRevit/images/reinstall.png)

If you answer No, It'll ask you if you want to uninstall the tool. The setup script will remove the `.addin` files and `%pyrevit%` environment variable when uninstalling pyRevit.

![Reinstall](http://eirannejad.github.io/pyRevit/images/uninstallComplete.png)


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
- Neil Reilly for the handy introduction and installation [video](https://www.youtube.com/watch?v=71rvCspWNHs).
- [Gui Talarico](https://github.com/gtalarico). For testing and new tool ideas and contributing python scripts to the library.
- [git-scm](https://git-scm.com) for the open source, portable git for windows.

**NOTE**: If you are not on this list, but believe you should be, please contact me!
