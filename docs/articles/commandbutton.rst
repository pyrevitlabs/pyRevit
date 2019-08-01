Keyboard Shortcuts
==================

.. _shiftclick:

Shift-Click: Config Script
------------------------------------

Each pyRevit command bundle can contain two scripts:

    ``*script.py`` is the main script.

    ``*config.py`` is the Config script.

SHIFT-clicking on a ui button will run the config script.
This config script is generally used to configure the main tool.
Try Shift clicking on the Match tool in pyRevit > Modify panel and see the configuration window.
Then try Shift clicking on the Settings tool in pyRevit panel slide-out and see what it does.

If you don't define the configuration script, you can check the value of ``__shiftclick__``
in your scripts to change script behaviour. This is the method that the
Settings command is using to open the config file location in explorer:

.. code-block:: python

    if __shiftclick__:
        do_task_A()
    else:
        do_task_B()



Ctrl-Click: Debug Mode
----------------------

CTRL-clicking on a ui button will run the script in DEBUG mode and will allow the script to print all debug messages.
You can check the value of ``__forceddebugmode__`` variable to see if the script is running in Debug mode to change script behaviour if neccessary.

.. code-block:: python

    if __forceddebugmode__:
    	do_task_A()
    else:
    	do_task_B()



Alt-Click: Show Script file in Explorer
---------------------------------------

ALT-clicking on a ui button will show the associated script file in windows explorer.



Ctrl-Shift-Alt-Click: Reload Engine
-----------------------------------

If you're using pyRevit Rocket mode, this keyboard combination will force pyRevit
to discard the cached engine for this command and use a new fresh engine. If you are
developing scripts for pyRevit and using external modules, you'll need to use this
keyboard combination after changes to the imported module source codes. Since the
modules are already imported in the cached engine, you'd need a new fresh engine
to reload the modules.



Shift-Win-Click: pyRevit Button Context Menu
--------------------------------------------

Shows the context menu for the pyRevit command. See image below:
