# pyRevit for Autodesk Revit®

[Browse to pyRevit blog to learn more and download the installation.](http://eirannejad.github.io/pyRevit/)

- In it's simplest form, it's a folder of IronPython `.py` scripts for Autodesk Revit.
- There is also an IronPython helper script, named `__init__.py`, that creates a ribbon tab and creates UI buttons for the IronPython scripts at Revit startup. Adding a button to this tab is as easy as adding a IronPython script file to the pyRevit folder and reloading pyRevit. 

## Branches

Branches in this repository are used for features, development, and different components of the pyRevit library. Here is a quick explanation on the purpose for each branch:

####Master Branches:

The setup program clones these two branches into your machine at installation.

-	`master` : Master branch holds the main published repository. (It's currently empty but will hold the library scripts for final release of version 3.) It also includes this Readme file that provides a link to the [pyRevit blog](http://eirannejad.github.io/pyRevit/).
- `loader` : This is the main branch for the loader script that creates UI buttons for the library scripts. It also includes the compiled `.dll` binaries for `RevitPythonLoader` that is needed to create the buttons.

####Develop Branches:

- `verThreeDev` : This is the beta version code for the pyRevit library. The current beta installer, clones this branch to your machine. This will be pulled to master for the final version.

####Misc Branches:

- `gh-pages` : The source for [pyRevit blog](http://eirannejad.github.io/pyRevit/).


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
