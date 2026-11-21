# Runtime variables

!!! warning ""

    It is strongly advised not to read or write values from these variables unless necessary. The pyRevit module provides wrappers around these variables that are safe to use.

Variables listed below are provided for every python script in pyRevit. The suggested method to access these global variables is also shown here. This way you will mask your scripts against interal pyRevit runtime changes should the name of these global variables ever change.

## Runtime Global Variable

#### Revit Environment

```python

# Revit UIApplication is accessible through:
__revit__

# Command data provided to this command by Revit
# is accessible through:
__commanddata__

# selection of elements provided to this command by Revit
__elements__

# instance of ui button object for the running command
__uibutton__
```

#### pyRevit Runtime Types

```python

# pyRevit executing engine id
__cachedengineid__

# This variable is True if command is being run
# in a cached engine
__cachedengine__

# pyRevit external command object wrapping the
# command being run
__scriptruntime__
```

#### Bundle Info

```python
# information about the pyrevit command being run

__commandpath__           # main script path
__configcommandpath__     # config script path
__commandname__           # command name
__commandbundle__         # command bundle name
__commandextension__      # command bundle name
__commanduniqueid__       # command bundle name
__commandcontrolid__      # command control id
```

#### Execution Info

```python

# unique id for this execution
__execid__

# timestamp of this execution
__timestamp__

# This variable is True if user CTRL-Clicks the button
__forceddebugmode__

# This variable is True if user SHIFT-Clicks the button
__shiftclick__

# results dictionary
__result__
```

## Safe Access Method

```python
from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import revit

# UIApplication
HOST_APP.uiapp

# command data
EXEC_PARAMS.command_data

# selected elements
selection = revit.get_selection()

# ui button
EXEC_PARAMS.command_uibutton
```

```python
from pyrevit import EXEC_PARAMS

# pyRevit executing engine id
EXEC_PARAMS.engine_id

# Cached engine
EXEC_PARAMS.cached_engine

# pyRevit external command
EXEC_PARAMS.script_runtime
```

```python
from pyrevit import EXEC_PARAMS

EXEC_PARAMS.command_path         # main script path
EXEC_PARAMS.command_config_path  # config script path
EXEC_PARAMS.command_name         # command name
EXEC_PARAMS.command_bundle       # command bundle name
EXEC_PARAMS.command_extension    # command bundle name
EXEC_PARAMS.command_uniqueid     # command bundle name
EXEC_PARAMS.command_controlid    # command bundle name
```

```python
from pyrevit import EXEC_PARAMS

# unique id for this execution
EXEC_PARAMS.exec_id

# timestamp of this execution
EXEC_PARAMS.exec_timestamp

# if command is in debug mode
EXEC_PARAMS.debug_mode

# if command is in config mode
EXEC_PARAMS.config_mode

# gain access to the command results dict for telemetry
from pyrevit import script
results = script.get_results()
```

