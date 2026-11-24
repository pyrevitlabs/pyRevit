# Your first .NET command

!!! warning ""

    Take a look at the [Create Your First Command](first-command.md)  for information about setting up your first extension. This article explains how to create a .NET script in pyRevit. The rest is the same.

### Writing The Script

pyRevit supports C# or VB.Net for .NET bundles. Create a `.cs` or `.vb` script inside your bundle. The .NET bundles are a bit more strict so a little scaffolding is necessary to make the script work.

Specifically, we need to define a class that implements [**IExternalCommand**](https://api.apidocs.co/resolve/revit/2020/?asset_id=T:Autodesk.Revit.UI.IExternalCommand) interface. Return any of the [**Result**](https://apidocs.co/apps/revit/2020/e6cebb3c-0c3f-7dc4-2063-e5df0a00b2f5.htm) options from your command depending on the outcome. You can use the examples below as templates. The `Execute` method can contain your .NET code. Every time the script code changes, pyRevit will automatically recompile and runs the new version.

See the page below for detailed information on pyRevit features available to .NET bundles.

- [Anatomy of .NET (C#, VB) Scripts](../scripting/dotnet.md)

```csharp
using System;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

namespace HelloWorld {
   public class Test2 : IExternalCommand {
      public Result Execute(ExternalCommandData revit,
                            ref string message, ElementSet elements) {

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

Public Class HelloWorld
    Implements IExternalCommand

    Public Function Execute(ByVal revit As ExternalCommandData, _
                            ByRef message As String, _
                            ByVal elements As ElementSet) As Autodesk.Revit.UI.Result _
                                Implements IExternalCommand.Execute
           Return Autodesk.Revit.UI.Result.Succeeded
    End Function
End Class
```

!!! tip ""

    See [Anatomy of .NET (C#, VB) Scripts](../scripting/dotnet.md)  
