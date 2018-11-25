Anatomy of a pyRevit Script
===========================

pyRevit provides a few basic services to python scripts that use its engine.
These fuctionalities are accessible through a few high level modules.
This article is a quick look at these services and their associated
python modules.


Script Metadata Variables
-------------------------

pyRevit looks for certain global scope variables in each scripts that provide
metadata about the script and follow the ``__<name>__`` format.


__title__
^^^^^^^^^

.. image:: https://via.placeholder.com/150

**Button Title**: When using the bundle name as the
button name in Revit UI is not desired, or you want to add a newline
character to the command name to better display the butonn name inside
Revit UI Panel, you can define the ``__title__`` variable in your script
and set it to the desired button title.


    .. code-block:: python

        __title__ = 'Sample\\nCommand'


__doc__
^^^^^^^

.. image:: https://via.placeholder.com/400x150

**Button Tooltip**: Tooltips are displayed similar to the
other buttons in Revit interface. You can define the tooltip for a script
using the doscstring at the top of the script or by explicitly defining
``__doc__`` metadata variable.


    .. code-block:: python

        # defining tooltip as the script docstring
        """You can place the docstring (tooltip) at the top of the script file.
        This serves both as python docstring and also button tooltip in pyRevit.
        You should use triple quotes for standard python docstrings."""


    .. code-block:: python

        # defining tooltip by setting metadata variable
        __doc__ = 'This is the text for the button tooltip associated with this script.'


__author__
^^^^^^^^^^

.. image:: https://via.placeholder.com/400x50

**Script Author**: You can define the script author as shown below.
This will show up on the button tooltip.


    .. code-block:: python

        __author__ = 'Ehsan Iran-Nejad'


__helpurl__
^^^^^^^^^^^

**F1 Shortcut Help Url**: xx

__min_revit_ver__
^^^^^^^^^^^^^^^^^

**Min Revit Version Required**: xx

__max_revit_ver__
^^^^^^^^^^^^^^^^^

**Max Revit Version Supported**: xx

__beta__
^^^^^^^^

**Script In Beta**: xx

__context__
^^^^^^^^^^^

**Command Availability**: Revit commands use standard ``IExternalCommandAvailability`` class to let Revit
know if they are available in different contexts. For example, if a command needs
to work on a set of elements, it can tell Revit to deactivate the button unless
the user has selected one or more elements.

In pyRevit, command availability is set through the ``__context__`` variable.
Currently, pyRevit support three types of command availability types.

.. code-block:: python

    # Tool activates when at least one element is selected
    __context__ = 'Selection'

    # Tools are active even when there are no documents available/open in Revit
    __context__ = 'zerodoc'

    # Tool activates when all selected elements are of the given category or categories
    __context__ = '<Element Category>'
    __context__ = ['<Element Category>', '<Element Category>']


``<Element Category>`` can be any of the standard Revit element categories.
See :ref:`appendix-b` for a full list of system categories.
You can use the ``List`` tool under ``pyRevit > Spy`` and list the standard categories.

Here are a few examples:


    .. code-block:: python

        # Tool activates when all selected elements are of the given category

        __context__ = 'Doors'
        __context__ = 'Walls'
        __context__ = 'Floors'
        __context__ = ['Space Tags', 'Spaces']


.. _scriptmodule:

pyrevit.script Module
---------------------

All pyRevit scripts should use the :mod:`pyrevit.script` module to access pyRevit
functionality unless listed otherwise. pyRevit internals are subject to changes
and accessing them directly is not suggested.

Here is a list of supported modules for pyRevit scripts. Examples of using
the functionality in these modules are provided on this page.

:mod:`pyrevit.script`

    This module provides access to output window (:mod:`pyrevit.output`),
    logging (:mod:`pyrevit.coreutils.logger`),
    temporary files (:mod:`pyrevit.coreutils.appdata`),
    and other misc features.
    See the module page for usage examples and full documentation of all available functions.


Logging
^^^^^^^

You can get the default logger for the script using :func:`pyrevit.script.get_logger`.

.. code-block:: python

    from pyrevt import script

    logger = script.get_logger()

    logger.info('Test Log Level :ok_hand_sign:')

    logger.warning('Test Log Level')

    logger.critical('Test Log Level')

Critical and warning messages are printed in color for clarity. Normally debug messages are not printed.
you can hold CTRL and click on a command button to put that command in DEBUG mode and see all its debug messages

.. code-block:: python

    logger.debug('Yesss! Here is the debug message')


Controlling Output Window
^^^^^^^^^^^^^^^^^^^^^^^^^

Each script can control its own output window:

.. code-block:: python

    from pyrevit import script

    output = script.get_output()

    output.set_height(600)
    output.get_title()
    output.set_title('More control please!')

See :doc:`outputfeatures` for more info.


Script Config
^^^^^^^^^^^^^

Each script can save and load configuration pyRevit's user configuration file:

See :doc:`../pyrevit/output/init` for more examples.

See :func:`pyrevit.script.get_config` and :func:`pyrevit.script.save_config` for the individual functions used here.

.. code-block:: python

    from pyrevit import script

    config = script.get_config()

    # set a new config parameter: firstparam
    config.firstparam = True

    # saving configurations
    script.save_config()

    # read the config parameter value
    if config.firstparam:
        do_task_A()


Logging Results
^^^^^^^^^^^^^^^

pyRevit has a usage logging system that can record all tool usages to either a json
file or to a web server. Scripts can return custom data to this logging system.

In example below, the script reports the amount of time it saved to the logging system:

.. code-block:: python

    from pyrevit import script

    results = script.get_results()
    results.timesaved = 10


Using Temporary Files
^^^^^^^^^^^^^^^^^^^^^

Scripts can create 3 different types of data files:

* **Universal files**

    These files are not marked by host Revit version and could be shared between all Revit versions and instances.
    These data files are saved in pyRevit's appdata directory and are NOT cleaned up at Revit restarts.

    See :func:`pyrevit.script.get_universal_data_file`

    ..  note::
       Script should take care of cleaning up these data files.

    .. code-block:: python

        # provide a unique file id and file extension
        # Method will return full path of the data file
        from pyrevit import script
        script.get_universal_data_file(file_id, file_ext)


* **Data files**

    These files are marked by host Revit version and could be shared between instances of host Revit version
    Data files are saved in pyRevit's appdata directory and are NOT cleaned up when Revit restarts.

    See :func:`pyrevit.script.get_data_file`

    ..  note::
        Script should take care of cleaning up these data files.

    .. code-block:: python

        # provide a unique file id and file extension
        # Method will return full path of the data file
        from pyrevit import script
        script.get_data_file(file_id, file_ext)

* **Instance Data files**

    These files are marked by host Revit version and process Id and are only available to current Revit instance. This avoids any conflicts between similar scripts running under two or more Revit instances.
    Data files are saved in pyRevit's appdata directory (with extension `.tmp`) and ARE cleaned up when Revit restarts.

    See :func:`pyrevit.script.get_instance_data_file`

    .. code-block:: python

        # provide a unique file id and file extension
        # Method will return full path of the data file
        from pyrevit import script
        script.get_instance_data_file(file_id)


* **Document Data files**

    (Shared only between instances of host Revit version): These files are marked by host Revit version and name of Active Project and could be shared between instances of host Revit version.
    Data files are saved in pyRevit's appdata directory and are NOT cleaned up when Revit restarts.

    See :func:`pyrevit.script.get_document_data_file`

    ..  note::
        Script should take care of cleaning up these data files.

    .. code-block:: python

        # provide a unique file id and file extension
        # Method will return full path of the data file
        from pyrevit import script
        script.get_document_data_file(file_id, file_ext)

        # You can also pass a document object to get a data file for that
        # document (use document name in file naming)
        script.get_document_data_file(file_id, file_ext, doc)


.. _appendix-a:

Appendix A: Builtin Parameters Provided by pyRevit Engine
---------------------------------------------------------

Variables listed below are provided for every script in pyRevit.

..  note::
    It's strongly advised not to read or write values from these variables unless
    necessary. The `pyrevit` module provides wrappers around these variables that are safe to use.

.. code-block:: python

    # Revit UIApplication is accessible through:
    __revit__

    # Command data provided to this command by Revit is accessible through:
    __commandData__

    # selection of elements provided to this command by Revit
    __elements__

    # pyRevit engine manager that is managing this engine
    __ipyenginemanager__

    # This variable is True if command is being run in a cached engine
    __cachedengine__

    # pyRevit external command object wrapping the command being run
    __externalcommand__

    # information about the pyrevit command being run
    __commandpath__             # main script path
    __alternatecommandpath__    # alternate script path
    __commandname__             # command name
    __commandbundle__           # command bundle name
    __commandextension__        # command extension name
    __commanduniqueid__         # command unique id

    # This variable is True if user CTRL-Clicks the button
    __forceddebugmode__

    # This variable is True if user SHIFT-Clicks the button
    __shiftclick__

    # results dictionary
    __result__


.. _appendix-b:

Appendix B: System Category Names
---------------------------------

.. code-block:: text

    Adaptive Points
    Air Terminal Tags
    Air Terminals
    Analysis Display Style
    Analysis Results
    Analytical Beam Tags
    Analytical Beams
    Analytical Brace Tags
    Analytical Braces
    Analytical Column Tags
    Analytical Columns
    Analytical Floor Tags
    Analytical Floors
    Analytical Foundation Slabs
    Analytical Isolated Foundation Tags
    Analytical Isolated Foundations
    Analytical Link Tags
    Analytical Links
    Analytical Node Tags
    Analytical Nodes
    Analytical Slab Foundation Tags
    Analytical Spaces
    Analytical Surfaces
    Analytical Wall Foundation Tags
    Analytical Wall Foundations
    Analytical Wall Tags
    Analytical Walls
    Annotation Crop Boundary
    Area Load Tags
    Area Tags
    Areas
    Assemblies
    Assembly Tags
    Boundary Conditions
    Brace in Plan View Symbols
    Cable Tray Fitting Tags
    Cable Tray Fittings
    Cable Tray Runs
    Cable Tray Tags
    Cable Trays
    Callout Boundary
    Callout Heads
    Callouts
    Cameras
    Casework
    Casework Tags
    Ceiling Tags
    Ceilings
    Color Fill Legends
    Columns
    Communication Device Tags
    Communication Devices
    Conduit Fitting Tags
    Conduit Fittings
    Conduit Runs
    Conduit Tags
    Conduits
    Connection Symbols
    Contour Labels
    Crop Boundaries
    Curtain Grids
    Curtain Panel Tags
    Curtain Panels
    Curtain System Tags
    Curtain Systems
    Curtain Wall Mullions
    Data Device Tags
    Data Devices
    Detail Item Tags
    Detail Items
    Dimensions
    Displacement Path
    Door Tags
    Doors
    Duct Accessories
    Duct Accessory Tags
    Duct Color Fill
    Duct Color Fill Legends
    Duct Fitting Tags
    Duct Fittings
    Duct Insulation Tags
    Duct Insulations
    Duct Lining Tags
    Duct Linings
    Duct Placeholders
    Duct Systems
    Duct Tags
    Ducts
    Electrical Circuits
    Electrical Equipment
    Electrical Equipment Tags
    Electrical Fixture Tags
    Electrical Fixtures
    Electrical Spare/Space Circuits
    Elevation Marks
    Elevations
    Entourage
    Filled region
    Fire Alarm Device Tags
    Fire Alarm Devices
    Flex Duct Tags
    Flex Ducts
    Flex Pipe Tags
    Flex Pipes
    Floor Tags
    Floors
    Foundation Span Direction Symbol
    Furniture
    Furniture System Tags
    Furniture Systems
    Furniture Tags
    Generic Annotations
    Generic Model Tags
    Generic Models
    Grid Heads
    Grids
    Guide Grid
    HVAC Zones
    Imports in Families
    Internal Area Load Tags
    Internal Line Load Tags
    Internal Point Load Tags
    Keynote Tags
    Level Heads
    Levels
    Lighting Device Tags
    Lighting Devices
    Lighting Fixture Tags
    Lighting Fixtures
    Line Load Tags
    Lines
    Masking Region
    Mass
    Mass Floor Tags
    Mass Tags
    Matchline
    Material Tags
    Materials
    Mechanical Equipment
    Mechanical Equipment Tags
    MEP Fabrication Containment
    MEP Fabrication Containment Tags
    MEP Fabrication Ductwork
    MEP Fabrication Ductwork Tags
    MEP Fabrication Hanger Tags
    MEP Fabrication Hangers
    MEP Fabrication Pipework
    MEP Fabrication Pipework Tags
    Multi-Category Tags
    Multi-Rebar Annotations
    Nurse Call Device Tags
    Nurse Call Devices
    Panel Schedule Graphics
    Parking
    Parking Tags
    Part Tags
    Parts
    Pipe Accessories
    Pipe Accessory Tags
    Pipe Color Fill
    Pipe Color Fill Legends
    Pipe Fitting Tags
    Pipe Fittings
    Pipe Insulation Tags
    Pipe Insulations
    Pipe Placeholders
    Pipe Segments
    Pipe Tags
    Pipes
    Piping Systems
    Plan Region
    Planting
    Planting Tags
    Plumbing Fixture Tags
    Plumbing Fixtures
    Point Clouds
    Point Load Tags
    Project Information
    Property Line Segment Tags
    Property Tags
    Railing Tags
    Railings
    Ramps
    Raster Images
    Rebar Cover References
    Rebar Set Toggle
    Rebar Shape
    Reference Lines
    Reference Planes
    Reference Points
    Render Regions
    Revision Cloud Tags
    Revision Clouds
    Roads
    Roof Tags
    Roofs
    Room Tags
    Rooms
    Routing Preferences
    Schedule Graphics
    Scope Boxes
    Section Boxes
    Section Line
    Section Marks
    Sections
    Security Device Tags
    Security Devices
    Shaft Openings
    Sheets
    Site
    Site Tags
    Space Tags
    Spaces
    Span Direction Symbol
    Specialty Equipment
    Specialty Equipment Tags
    Spot Coordinates
    Spot Elevation Symbols
    Spot Elevations
    Spot Slopes
    Sprinkler Tags
    Sprinklers
    Stair Landing Tags
    Stair Paths
    Stair Run Tags
    Stair Support Tags
    Stair Tags
    Stair Tread/Riser Numbers
    Stairs
    Structural Annotations
    Structural Area Reinforcement
    Structural Area Reinforcement Symbols
    Structural Area Reinforcement Tags
    Structural Beam System Tags
    Structural Beam Systems
    Structural Column Tags
    Structural Columns
    Structural Connection Tags
    Structural Connections
    Structural Fabric Areas
    Structural Fabric Reinforcement
    Structural Fabric Reinforcement Symbols
    Structural Fabric Reinforcement Tags
    Structural Foundation Tags
    Structural Foundations
    Structural Framing
    Structural Framing Tags
    Structural Internal Loads
    Structural Load Cases
    Structural Loads
    Structural Path Reinforcement
    Structural Path Reinforcement Symbols
    Structural Path Reinforcement Tags
    Structural Rebar
    Structural Rebar Coupler Tags
    Structural Rebar Couplers
    Structural Rebar Tags
    Structural Stiffener Tags
    Structural Stiffeners
    Structural Truss Tags
    Structural Trusses
    Switch System
    Telephone Device Tags
    Telephone Devices
    Text Notes
    Title Blocks
    Topography
    View Reference
    View Titles
    Viewports
    Views
    Wall Tags
    Walls
    Window Tags
    Windows
    Wire Tags
    Wires
    Zone Tags
