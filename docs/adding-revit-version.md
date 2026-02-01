# Adding Support for a New Revit Version

This guide explains the step-by-step process to add support for a new Revit version to pyRevit.

## Prerequisites

Before starting, gather the following information:

1. **Revit Version Year** (e.g., 2028)
2. **Target .NET Framework**:
   - Revit 2024 and earlier: `net48`
   - Revit 2025-2026: `net8.0-windows`
   - Revit 2027+: `net10.0-windows`
3. **Check if a new .NET version is required** - If the new Revit uses a different .NET version than previous releases, additional steps are needed (see sections 4 and 5)

---

## Step 1: Create the Runtime Project

Create a new runtime project for the Revit version.

### 1.1 Copy an existing project folder

```shell
cd dev/pyRevitLabs.PyRevit.Runtime
cp -r 2027 2028
```

### 1.2 Rename and update the project file

Rename `pyRevitLabs.PyRevit.Runtime.2027.csproj` to `pyRevitLabs.PyRevit.Runtime.2028.csproj` and update its contents:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <UseWpf>true</UseWpf>
    <UseWindowsForms>true</UseWindowsForms>
  </PropertyGroup>
  
  <PropertyGroup>
    <RevitVersion>2028</RevitVersion>
    <TargetFramework>net10.0-windows</TargetFramework>
  </PropertyGroup>
</Project>
```

!!! note
    Adjust the `TargetFramework` based on which .NET version the new Revit uses.

---

## Step 2: Update Build Configuration

### 2.1 Add version constants

Edit `dev/Directory.Build.targets` and add a new `PropertyGroup` for the version constants:

```xml
<PropertyGroup Condition="'$(RevitVersion)' == '2028'">
    <DefineConstants>$(DefineConstants);REVIT2028;REVIT2021_OR_GREATER;REVIT2022_OR_GREATER</DefineConstants>
</PropertyGroup>
```

### 2.2 Add target framework mapping (if new .NET version)

If the new Revit uses a new .NET version, add a mapping in the `NetFolder` section:

```xml
<PropertyGroup>
    <NetFolder Condition="'$(TargetFramework)' == 'net48'">netfx</NetFolder>
    <NetFolder Condition="'$(TargetFramework)' == 'net8.0-windows'">netcore</NetFolder>
    <NetFolder Condition="'$(TargetFramework)' == 'net10.0-windows'">netcore</NetFolder>
    <!-- Add new framework mapping here if needed -->
</PropertyGroup>
```

### 2.3 Add default version mapping (if new .NET version)

```xml
<PropertyGroup>
    <RevitVersion Condition="'$(RevitVersion)' == '' and '$(TargetFramework)' == 'net48'">2017</RevitVersion>
    <RevitVersion Condition="'$(RevitVersion)' == '' and '$(TargetFramework)' == 'net8.0-windows'">2025</RevitVersion>
    <RevitVersion Condition="'$(RevitVersion)' == '' and '$(TargetFramework)' == 'net10.0-windows'">2027</RevitVersion>
    <!-- Add new default here if needed -->
</PropertyGroup>
```

---

## Step 3: Copy Support Libraries

Copy the `Xceed.Wpf.AvalonDock.dll` from the previous version:

```shell
mkdir dev/libs/Revit/2028
cp dev/libs/Revit/2027/Xceed.Wpf.AvalonDock.dll dev/libs/Revit/2028/
```

This DLL is required for the dockable console functionality in Revit 2018+.

---

## Step 4: Update Host Registry

Add entries for the new Revit builds in `bin/pyrevit-hosts.json`.

Example entry:

```json
{
    "build": "20270115_1200",
    "meta": {
        "schema": "1.0",
        "source": "https://www.autodesk.com/support/technical/article/..."
    },
    "notes": "",
    "product": "Autodesk Revit",
    "release": "Revit 2028",
    "target": "x64",
    "version": "28.0.0.0"
}
```

!!! note
    Build numbers are released by Autodesk with each update. Add new entries as updates are released.

---

## Step 5: CI/CD Updates (New .NET Version Only)

If the new Revit requires a new .NET version, update the GitHub Actions workflow.

### 5.1 Add .NET SDK setup

Edit `.github/workflows/main.yml` and add a new setup step:

```yaml
- name: Prepare .NET XX.0
  uses: actions/setup-dotnet@v5
  with:
    dotnet-version: XX.0.x
```

---

## Step 6: Installer Updates (New .NET Version Only)

### 6.1 Add dependency procedure

Edit `release/CodeDependencies.iss` and add new procedures for the .NET runtime.

Copy the latest procedures from the upstream [InnoDependencyInstaller](https://github.com/DomGries/InnoDependencyInstaller/blob/master/CodeDependencies.iss) repository. Look for procedures like `Dependency_AddDotNetXX0` and `Dependency_AddDotNetXX0Desktop`.

Example (based on .NET 10):

```pascal
procedure Dependency_AddDotNet110;
begin
  // https://dotnet.microsoft.com/download/dotnet/11.0
  if not Dependency_IsNetCoreInstalled('Microsoft.NETCore.App', 11, 0, 0) then begin
    Dependency_Add('dotnet110' + Dependency_ArchSuffix + '.exe',
      '/lcid ' + IntToStr(GetUILanguage) + ' /passive /norestart',
      '.NET Runtime 11.0.0' + Dependency_ArchTitle,
      Dependency_String('https://builds.dotnet.microsoft.com/dotnet/Runtime/11.0.0/dotnet-runtime-11.0.0-win-x86.exe', 'https://builds.dotnet.microsoft.com/dotnet/Runtime/11.0.0/dotnet-runtime-11.0.0-win-x64.exe'),
      '', False, False);
  end;
end;

procedure Dependency_AddDotNet110Desktop;
begin
  // https://dotnet.microsoft.com/download/dotnet/11.0
  if not Dependency_IsNetCoreInstalled('Microsoft.WindowsDesktop.App', 11, 0, 0) then begin
    Dependency_Add('dotnet110desktop' + Dependency_ArchSuffix + '.exe',
      '/lcid ' + IntToStr(GetUILanguage) + ' /passive /norestart',
      '.NET Desktop Runtime 11.0.0' + Dependency_ArchTitle,
      Dependency_String('https://builds.dotnet.microsoft.com/dotnet/WindowsDesktop/11.0.0/windowsdesktop-runtime-11.0.0-win-x86.exe', 'https://builds.dotnet.microsoft.com/dotnet/WindowsDesktop/11.0.0/windowsdesktop-runtime-11.0.0-win-x64.exe'),
      '', False, False);
  end;
end;
```

!!! tip
    The upstream repository is regularly updated with the latest .NET runtime download URLs. Check there first for ready-to-use procedures.

### 6.2 Call the dependency in the installer

Edit `release/pyrevit.iss` and add calls in the `InitializeSetup` function:

```pascal
function InitializeSetup: Boolean;
begin
  // .NET 8 for Revit 2025-2026
  Dependency_AddDotNet80;
  Dependency_AddDotNet80Desktop;
  // .NET 10 for Revit 2027+
  Dependency_AddDotNet100;
  Dependency_AddDotNet100Desktop;
  // .NET XX for Revit 20YY+ (add new dependencies here)
  Result := True;
end;
```

---

## Step 7: Handle Revit API Breaking Changes

Check the Revit API release notes for breaking changes. Common patterns include:

### Conditional compilation

Use preprocessor directives to handle API differences:

```csharp
#if REVIT2028_OR_GREATER
    // New API for 2028+
    element.NewMethod();
#else
    // Legacy API
    element.OldMethod();
#endif
```

### Adding new version constants

If needed, add new `_OR_GREATER` constants in `dev/Directory.Build.targets`:

```xml
<PropertyGroup Condition="'$(RevitVersion)' == '2028'">
    <DefineConstants>$(DefineConstants);REVIT2028;REVIT2021_OR_GREATER;REVIT2022_OR_GREATER;REVIT2028_OR_GREATER</DefineConstants>
</PropertyGroup>
```

---

## Step 8: Build and Test

### 8.1 Build the products

```shell
pipenv run pyrevit build labs Debug
pipenv run pyrevit build products Debug
```

### 8.2 Attach and test

```shell
.\bin\pyrevit.exe attach dev default --installed
```

### 8.3 Verify in Revit

1. Launch the new Revit version
2. Check that pyRevit loads without errors
3. Test core functionality (ribbon, scripts, console)

---

## Quick Reference: Key Files

| File | Purpose |
|------|---------|
| `dev/pyRevitLabs.PyRevit.Runtime/YYYY/*.csproj` | Runtime project per Revit version |
| `dev/Directory.Build.targets` | Version constants and framework mappings |
| `dev/Directory.Build.props` | Common project properties and NuGet packages |
| `dev/libs/Revit/YYYY/` | Version-specific DLLs (Xceed.Wpf.AvalonDock) |
| `bin/pyrevit-hosts.json` | Revit build registry for version detection |
| `.github/workflows/main.yml` | CI/CD pipeline configuration |
| `release/CodeDependencies.iss` | .NET runtime installer procedures |
| `release/pyrevit.iss` | Main pyRevit installer script |

---

## Troubleshooting

### Build errors about missing types

This usually means a Revit API has changed. Check the API documentation and add conditional compilation (`#if REVITxxxx_OR_GREATER`).

### Runtime errors in new Revit version

Check for reflection-based code that may behave differently on new .NET versions. Submodules like IronPython may need updates for new .NET compatibility.

### Xceed.Wpf.AvalonDock errors

Ensure the DLL was copied to the correct `dev/libs/Revit/YYYY/` folder.
