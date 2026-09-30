# Adding Support for a New Revit Version

This guide explains the step-by-step process to add support for a new Revit version to pyRevit.

## Prerequisites

Before starting, gather the following information:

1. **Revit Version Year** (e.g., 2028)
2. **Target .NET Framework**:
   - Revit 2021-2024: `net48`
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
    <RevitVersion Condition="'$(RevitVersion)' == '' and '$(TargetFramework)' == 'net48'">2021</RevitVersion>
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

This DLL is required for the dockable console functionality in supported Revit versions.

---

## Step 4: Update Host Registry

Add entries for the new Revit builds in [`release/pyrevit-hosts.json`](../release/pyrevit-hosts.json). CI copies this file into `bin/` at build time.

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
    "release": "2028",
    "target": "x64",
    "version": "28.0.0.0"
}
```

!!! note
    Build numbers are released by Autodesk with each update. Add new entries as updates are released.

### The `release` field is a display name, not an identity

`release` holds the title Autodesk uses on the matching release-notes page: the dotted
version, then `Update` for a minor release or `Hotfix`/`Update` for a point fix, exactly
as Autodesk spells it. Autodesk's own usage is not uniform — point fixes are `Hotfix` up
to 2023.0 and `Update` from 2023.1 on — so the file reproduces that rather than smoothing
it. The `2021 First Customer Ship` and `2027 Preview Release` names describe a
distribution channel, not a version, and are kept verbatim.

Identity comes from `version` and `build`. `FindProductInfo` does compare `release`
(`RevitProduct.cs:165`), but the identifier it receives on the installed-products path is
the registry `DisplayVersion`, which for Revit 2021 and later is a four-part number such
as `25.5.0.57` — so `version` satisfies that match and `release` is close to inert there.
What `release` drives is display: `pyrevit revits`, `revits --csv`, `pyrevit env --json`,
attachment labels, and the Settings UI.

Two consequences for anyone editing this file:

- **Names must be unique.** When Autodesk ships two builds under one release-notes page
  (a base build and a follow-up install build), the second name carries its build date:
  `2025.4.3 Update` and `2025.4.3 Update (20250815)`. A shared name is not a cosmetic
  problem — `FindProductInfo` resolves a tied match by returning the first row
  (`RevitProduct.cs:191`), so the second build would silently be reported as the first.
- **Do not put whitespace before a four-digit year.** `GetProductYear`
  (`RevitProduct.cs:223`) matches `.*\s+(?<product_year>\d{4}).*`, so a name like
  `Revit 2028` starts resolving the product year from `release` instead of falling through
  to `version`, which changes what `IsSupported` and the attachment code paths do. Every
  name in the file is currently whitespace-free for this reason.

### Which Revit versions are listed

The host registry lists exactly the Revits the current pyRevit line supports, and
that floor is **Revit 2021** (`RevitProductData.MinimumSupportedProductYear`).
The C# loader replaced the legacy pure-Python loader, which was the only runtime
that ran on Revit 2020 and earlier, so those releases are not supported and are
deliberately absent from the file — the 6.5 line was the last to carry them.

Do not add a record below that floor to "fix" an install reporting the wrong
product. An older install is still detected, and reported as unsupported, so it
shows up in `pyrevit env` with a `not supported by this version of pyRevit` note
instead of silently standing in for a supported Revit.

### Build numbers are not unique

Autodesk reuses a build number across product years, so `build` alone does not
identify a host. Both of these ship build `20220517_1515`:

| release | version | build |
|---|---|---|
| 2020.2.9 | 20.2.90.12 | 20220517_1515 |
| 2021.1.7 Hotfix | 21.1.70.21 | 20220517_1515 |

(`2020.2.9` is shown as it was when that section was written; it predates the 2021 floor
described above and is no longer in the file.)

`RevitProductData.FindProductInfo` therefore treats a build match as a candidate
set and narrows it with the host's own identity — full file version first, then
install path, then the release named in the identifier. A candidate whose product
year contradicts the host's is dropped, and a candidate set that stays ambiguous
resolves to nothing rather than to an arbitrary record, so the caller falls back
to the binary's own version info.

Binding an install to the wrong record is not cosmetic: it reports the wrong
product year, which is what makes pyRevit load runtime assemblies built for a
different Revit and fail at load time with a `TypeLoadException`. When a build is
genuinely shared, an `Ambiguous host product` warning in the log names the records
involved; add the missing record to the registry rather than relying on a guess.

---

## Step 5: CI/CD Updates (New .NET Version Only)

If the new Revit requires a new .NET version, update the GitHub Actions workflow.

### 5.1 Add .NET SDK setup

Edit `.github/workflows/ci.yml` (and `wip.yml` / `release.yml` if they install their own SDKs) and add a new setup step:

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

The build is driven by the C# ModularPipelines project under `build/`. Run from `build/`:

```shell
cd build
dotnet run -c Debug -- ci
cd ..
```

For Release stamping on the new Revit version, run with `Build__Channel=release` (or `wip`) instead of the default `none`. See [`build/README.md`](../build/README.md) for full options.

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
| `release/pyrevit-hosts.json` | Revit build registry for version detection (staged to `bin/` by CI) |
| `.github/workflows/ci.yml`, `wip.yml`, `release.yml` | CI/CD pipeline configuration |
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
