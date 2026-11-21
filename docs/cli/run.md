# Run scripts on models

You can run a python script in any of the installed Revit versions from the command prompt.

```powershell
pyrevit run <script_file> [--revit=<revit_year>]

$ pyrevit run "C:\myscript.py"

# the execution environment information will be printed after completion
==> Execution Environment
Execution Id: "51066afe-022c-4dba-bdc5-d35d451b998f"
Product: <Revit product name> | Version: <version> | Build: <build>(<target>) | Language: <language code> | Path: "C:\Program Files\Autodesk\Revit <year>"
Clone: dev | Branch: "develop" | Version: "<version>" | Path: "...\pyRevit"
Engine: IPY2712PR (<folder>) | Kernel: IronPython | Version: 2712 | Runtime: True | Path: "<path of pyRevitLoader.dll>" | Desc: "<description>"
Script: "C:\myscript.py"
Working Directory: "...\Temp\51066afe-022c-4dba-bdc5-d35d451b998f"
Journal File: "...\Temp\51066afe-022c-4dba-bdc5-d35d451b998f\PyRevitRunner_51066afe-022c-4dba-bdc5-d35d451b998f.txt"
Manifest File: "...\Temp\51066afe-022c-4dba-bdc5-d35d451b998f\PyRevitRunner.addin"
Log File: "...\Temp\51066afe-022c-4dba-bdc5-d35d451b998f\PyRevitRunner_51066afe-022c-4dba-bdc5-d35d451b998f.log"
```

- `--purge`: Runner creates a temporary directory under `%TEMP%` for this execution. Specifying this option, will clear the temporary files after completion. This is helpful when running a script over many files.

If `--revit` option is not specified, the run command will use the newest installed version of Revit to run the command. You can however specify the version of Revit e.g. `--revit=2026`

At either case, pyRevit uses the clone and engine verison that is attached to Revit, to run the script; So make sure that pyRevit is already attached to the Revit version you are intending to use.

All the pyrevit modules are accessible inside the script.

#### Running a Script on Revit Models

You can also specify a single or multiple models to `pyrevit run` command. If a model is specified, the run command selects a version of Revit that is used to create that model by default. As the previous example, you can still manually specify which version of Revit to use. be aware that Revit will fail if the model version is newer, or needs to upgrade the model if it is an older version.

```powershell
pyrevit run <script_file> <model_file> [--revit=<revit_year>] [--purge]
pyrevit run <script_file> --models=<model_list_file> --revit=<revit_year> [--purge]

$ pyrevit run "C:\myscript.py" "C:\Model1.rvt"
$ pyrevit run "C:\myscript.py" --models="C:\All-My-Models.txt" --revit=2026

# target models will be listed at the end of env report
==> Target Models
C:\Models\Project_A.rvt
C:\Models\Project_B.rvt
```

- `<model_file>`: Path to a Revit model file.
- `--models=<model_list_file>`: Path to a text file listing multiple models, one per line. `--revit` is required with it.

**Important Note:**

**The run command does not attempt to open the model in Revit.** Opening a model is a complex process and has many configurations e.g. Opening central or detached, Workset configurations, etc. The run command uses a simple journal file to bootstrap Revit and avoids using complex journal structures to provide configurations on opening models since journals are heavily GUI based and could easily break in the future. Revit API provides ample functionality on opening models. It’s best practice to open the model inside your script.

The execution environment provides the global variable `__models__` set to a list of model file paths. Your script can read the models from this variable and attempt at opening each.

```python
from pyrevit import HOST_APP

# __models__ is set to a list of model file paths
# __models__ = ['C:\model1.rvt']
for model in __models__:
    uidoc = HOST_APP.uiapp.OpenAndActivateDocument(model)
    doc = uidoc.Document
    # do something here with the document
```

The developer is assumed to undestand the complexity and memory needs of the target models. Hence the run command does not provide any functionality to run multiple Revit instances on a single machine since it has very limited information about the resource needs of the target models.

The pyrevit run is intended to provide a simple interface for execution of python scripts on Revit model(s) from command line. You can write your own python or PowerShell scripts that processes the list of your models, understands their resource needs and the available resources of the host machine, and starts one or many `pyrevit run` instances to execute the scripts on the models.
