# C# and VB.NET scripts

!!! tip ""

    Start with the short introduction to scripts at [Create Your First Command](../tutorials/first-command.md) and [Create Your First .NET Command](../tutorials/first-dotnet-command.md)  

## Accessing Script Data

pyRevit provides access to some data about the .NET script being executed. To gain access to this data, import the `pyRevitLabs.PyRevit.Runtime.Shared` in your script, and define a public field on your command class with the type `ExecParams`

At execution time, pyRevit will fill this field. The `ExecParams` is defined as

```csharp
public class ExecParams {
    public string ExecId { get; }                // unique id of this execution
    public string ExecTimeStamp { get; }         // timestamp of this execution
    public string ScriptPath { get; }            // path to command script
    public string ConfigScriptPath { get; }      // path to command config script
    public string CommandUniqueId { get; }       // command unique id
    public string CommandControlId { get; }      // command control id
    public string CommandName { get; }           // command name
    public string CommandBundle { get; }         // command bundle full name with type
    public string CommandExtension { get; }      // command extension name
    public string HelpSource { get; }            // command help source
    public bool RefreshEngine { get; }           // if a new engine was requested through UI
    public bool ConfigMode { get; }              // if command is in config mode
    public bool DebugMode { get; }               // if command is in debug mode
    public bool ExecutedFromUI { get; }          // if command has been executed from UI
    public object UIButton { get; }              // the ribbon button of the command
}
```

Here is an example of accessing this data in C# and VB.NET

```csharp
using System;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

using pyRevitLabs.PyRevit.Runtime.Shared;

namespace HelloWorld
{
   public class MyCSharpCommand : IExternalCommand
   {
      // define the execparams field
      public ExecParams execParams;

      public Result Execute(ExternalCommandData revit, ref string message, ElementSet elements)
      {
         Console.WriteLine(execParams.ScriptPath);
         return Result.Succeeded;
      }
   }
}
```

```vbnet
Imports System
Imports Microsoft.VisualBasic

Imports Autodesk.Revit.UI
Imports Autodesk.Revit.DB

Imports pyRevitLabs.PyRevit.Runtime.Shared

Public Class MyVBCommand
    Implements IExternalCommand

    ' define the execparams field
    Public execParams As ExecParams

    Public Function Execute(ByVal revit As ExternalCommandData, _
                            ByRef message As String, _
                            ByVal elements As ElementSet) As Autodesk.Revit.UI.Result _
                                Implements IExternalCommand.Execute
            Console.WriteLine(execParams.ScriptPath)
            Return Autodesk.Revit.UI.Result.Succeeded
    End Function
End Class
```

## Accessing Logger

pyRevit provides access to an internal logger instance to help the script log data to the output window. To gain access to this data, import the `pyRevitLabs.NLog` in your script, and define a field on your command class with the type `Logger`

Here is an example of accessing this logger in C# and VB.NET

```csharp
using System;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

using pyRevitLabs.NLog;

namespace HelloWorld
{
   public class MyCSharpCommand : IExternalCommand
   {
      // define the logger field
      private Logger logger = LogManager.GetCurrentClassLogger();

      public Result Execute(ExternalCommandData revit, ref string message, ElementSet elements)
      {
         logger.Info("Logger works...");
         logger.Debug("Logger works...");
         return Result.Succeeded;
      }
   }
}
```

```vbnet
Imports System
Imports Microsoft.VisualBasic

Imports Autodesk.Revit.UI
Imports Autodesk.Revit.DB

Imports pyRevitLabs.NLog

Public Class MyVBCommand
    Implements IExternalCommand

    ' define the logger field
    Private logger As Logger = LogManager.GetCurrentClassLogger()

    Public Function Execute(ByVal revit As ExternalCommandData, _
                            ByRef message As String, _
                            ByVal elements As ElementSet) As Autodesk.Revit.UI.Result _
                                Implements IExternalCommand.Execute
            logger.Info("Logger works...")
            logger.Debug("Logger works...")
            Return Autodesk.Revit.UI.Result.Succeeded
    End Function
End Class
```
