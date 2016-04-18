**Question:** I'm an architect and engineer and love coding.
Unfortunately, I don't have the time and experience to code in complex languages that require special coding environments (e.g. Visual Studio) or need to be compiled and reloaded after each change.
I therefore like scripts.
I can create or modify them for a highly specific task, in the least amount of time, and get the job done.
I want to learn how to use IronPython for Revit and I need examples.
Do you know a good resource for that?

**Response:** Yes, definitely!

Take a look at [pyRevit](https://github.com/eirannejad/pyRevit).

***pyRevit*** is an IronPython script library for Revit.
However, it is not really written as an example library.
It is a working set of tools fully written in IronPython that explores the power of scripting for Revit and also adds some cool functionality.

Download and install it, launch Revit and you will note the new ***pyRevit*** tab that hosts buttons to launch all the scripts provided by the package to easily run them without the need to load them in [RevitPythonShell](https://github.com/architecture-building-systems/revitpythonshell) or some similar IronPython console.

You can also write your own scripts and add them to the tab.

There is even a Reload Scripts button than dynamically adds the new scripts to the current Revit session without the need to restart Revit.

All the scripts are provided in the `pyRevit` folder which is downloaded at installation.
You can look into them and learn how to use IronPython for Revit to perform different tasks.

Please refer to the [pyRevit](https://github.com/eirannejad/pyRevit) GitHub repository for links and instructions on how to install on your machine.


## Quick Look at some pyRevit Scripts

Let's take a quick look at some of the more useful scripts in this library:

### Selection Memory

A couple of scripts help you select object more efficiently in Revit. They are similar to the M+, M-, buttons on calculators where you can add or deduct values from memory and read the final value using the MR button.

Under the ***pyRevit*** tab, you'll find MAppend, MAppendOverwrite, MRead, MDeduct, and MClear buttons that add, add and overwrite, read, deduct, and clear the contents of the selection memory. Using these tools, you can navigate between multiple views and select objects, add them to the memory and when you're done, recall the selection. These tools work really well in combination with other selection tools under ***pyRevit*** tab. See images here for the tools and tooltips.

Each tooltip shows the button name, the script that the button is assciated with and a description of what the script does.

![MAppendOverWrite](http://eirannejad.github.io/pyRevit/images/mappendoverwrite.png)
![MRead](http://eirannejad.github.io/pyRevit/images/mread.png)
![OtherMemory](http://eirannejad.github.io/pyRevit/images/othermemory.png)

### Copy and Convert Legend Views

This set of scripts help you copy Legend Views to all other project open within a Revit session.
You can copy the Legends as Legend views or as Drafting views.

![CopyLegends](http://eirannejad.github.io/pyRevit/images/copylegends.png)

Two more scripts duplicate and convert Legend views to Drafting views and vice versa withing the same project.

![DuplicateLegends](http://eirannejad.github.io/pyRevit/images/convertlegends.png)

### Matching Element Graphic Overrides

This one is pretty obvious. Run the script, select your source object to pick up the style, and then one by one, select the destination objects to apply the graphic overrides. You can also navigate to other views and apply to objects within that view.

![MatchGraphicOverrides](http://eirannejad.github.io/pyRevit/images/matchgraphicoverrides.png)

***pyRevit*** provides many other powerful scripts, and most of them are really useful in a production environment.

![AnalsisAndModifyPallete](http://eirannejad.github.io/pyRevit/images/analysisandmodifypallete.png)
![ProjectPallete](http://eirannejad.github.io/pyRevit/images/projectpallete.png)
![DesktopPallete](http://eirannejad.github.io/pyRevit/images/desktoppallete.png)


## An Even Quicker but Deeper Look at Setting up pyRevit

Now let's take an even quicker and slightly deeper look at setting up [pyRevit](https://github.com/eirannejad/pyRevit):

In it's simplest form, it's a folder filled with `.py` IronPython scripts for Revit.

![pyrevitFolder](http://eirannejad.github.io/pyRevit/images/pyrevitfolder.png)

Since Revit itself does not provide an IronPython console, you
need [RevitPythonShell](https://github.com/architecture-building-systems/revitpythonshell) to
run them.

![RPSconsole](http://eirannejad.github.io/pyRevit/images/revitpythonshellconsole.png)

Let's say you have written a script that automatically designs amazing buildings and creates the Revit model and construction documents for it, and let's say you want to run this script as fast as you can and make a whole buncha money really quickly, but it takes time to open the command prompt every time, browse to the script file, open it and run it, so you naturally want something faster!

In order to make [pyRevit](https://github.com/eirannejad/pyRevit) more user friendly, it includes a helper script that finds all the other scripts and creates buttons for them in the Revit user interface.
This way. you can just click on the buttons instead of using the command prompt.

This script is appropriately called `__init__.py` and lives in
the [pyRevit](https://github.com/eirannejad/pyRevit) library root folder.

![initscript](http://eirannejad.github.io/pyRevit/images/initscript.png)

What's neat about this is that the user interface buttons only store the address to each script.
The script is reloaded and run every time the user clicks on the button.

This means that you can change a script on the fly while Revit is running, and the next time you click on the button, Revit will run the modified script.

But how do you tell Revit to run this script during start-up?

There are two ways to achieve this:

- The easy way:
[RevitPythonShell](https://github.com/architecture-building-systems/revitpythonshell) has
an option under `Configuration` to run an IronPython script at Revit startup. Just download
the [pyRevit](https://github.com/eirannejad/pyRevit) repository,
set the ***RevitPythonShell*** startup script address to the file address of the `__init__.py` script, and restart Revit.
Voila, the ***pyRevit*** tab appears.

- The even easier way:
Download the setup package from
the [pyRevit](https://github.com/eirannejad/pyRevit) GitHub repository and install.
Done! Launch your Revit and ***pyRevit*** will be there.

If you'd like to find out more about ***pyRevit*** and how to add your own scripts, visit the [pyRevit GitHub home page](https://github.com/eirannejad/pyRevit) and everything you want to know about it is provided.

Happy scripting!
