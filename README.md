# pyRevit for Autodesk Revit

PyRevit really has two sides:
- It is a script `__RPS__userSetup.py` that automates the process of creating user interface for your IronPython scripts
- It is also planning to be an IronPython package `import pyRevit` that will provide easier access to Revit's API.

## Setup process

Setup is very easy but a few important points first:
  - This tool requires installation of most recent version of [RevitPythonShell](https://github.com/architecture-building-systems/revitpythonshell)
  - These scripts are only tested under WINDOWS OS (7,8,10) and REVIT 2015-2016.
  - These scripts create their temporay files (e.g. the dynamic DLL module that contains the commands for each script) under user %temp% folder. But at every startup it'll cleanup after itself.

Now the setup process:
- Download the extract to your machine and place under a folder of your choice.
- Open Revit, go to RevitPythonShell > Configuration and assign `__RPS__userSetup.py` (part of this package) as the main startup script.
- Restart Revit. The `__RPS__userSetup.py` script will find all other scripts in its current directory and will create UI panels and buttons under 'pyRevit' ribbon tab. See below on how to add our own scripts and shortcuts to this tool.

## How to add your scripts:

And please feel free to fork, your own scripts, and send me pull requests. I'd be thrilled to add more tools and scripts to this for everyone to use.

## Documentation:

I'll figure out a system for the documentation soon. But for now please refer to tooltips for every script. These tooltips are included inside the script `.py` file as well. I'm open to all comments and suggestions :)

## Contribute

- Issue Tracker: https://github.com/eirannejad/pyRevit/issues
- Source Code: https://github.com/eirannejad/pyRevit

## Support

[stackoverflow](http://stackoverflow.com) (Note: use the ```pyRevit```, ``revit-api`` and ``revitpythonshell`` tags)

## License

This package is licensed under  GNU GENERAL PUBLIC LICENSE, Version 3, 29 June 2007.
See LICENSE.md for full license text.
See [this](http://choosealicense.com/) page for more information on licensing your work.

## Credits

I'd like to thank people listed here for their great contributions:
  * Daren Thomas (original version, maintainer of [RevitPythonShell](https://github.com/architecture-building-systems/revitpythonshell)) for creating RPS that this package is relying on and helping me out throught this process.
  * Jeremy Tammik (creator and maintainer of [RevitLookup](https://github.com/jeremytammik/RevitLookup))

**NOTE**: If you are not on this list, but believe you should be, please contact me!
