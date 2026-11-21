# Custom telemetry

pyRevit has a telemetry system that can record all tool usages to either a json file or to a web server. Scripts can return custom data to this telemetry system.

In example below, the script reports the amount of time it saved to the telemetry system:

```python
from pyrevit import script

# get the results dictionary object
results = script.get_results()

# set a value
results.timesaved = 10
```

The record sent to the telemetry system will have this information under `commandresults` field. See [Telemetry System](../../teams/telemetry.md) for the full record details.

```json
{
    // ...
    "commandresults": {
        "timesaved": 10
    },
    // ...
}
```
