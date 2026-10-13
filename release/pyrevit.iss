#define MyAppName "pyRevit"
#define MyAppUUID "f2a3da53-6f34-41d5-abbd-389ffa7f4d5f"
#define MyAppVersion "7.0.0.26278"
#define MyAppPublisher "pyRevitLabs"
#define MyAppURL "pyrevitlabs.io"
#include "CodeDependencies.iss"

[Setup]
; App information
AppId={#MyAppUUID}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright=Copyright © 2014-2026 pyRevitLabs.io
LicenseFile=..\LICENSE.txt
; Installer
DefaultGroupName={#MyAppName}
DisableDirPage=auto
DisableStartupPrompt=yes
DisableProgramGroupPage=yes
ChangesEnvironment=yes
;     path
DefaultDirName={userappdata}\{#MyAppName}-Master
UsePreviousAppDir=yes
;     mode
PrivilegesRequired=lowest
; Build info
OutputDir=..\dist
; Keep this list aligned with the installer assets staged by build/.
OutputBaseFilename=pyRevit_{#MyAppVersion}_signed
SetupIconFile=..\bin\pyrevit.ico
Compression=lzma
SolidCompression=yes
DisableWelcomePage=no
WizardStyle=classic
WizardImageFile=.\pyrevit.bmp
WizardSmallImageFile=.\pyrevit-banner.bmp
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Components]
Name: "core"; Description: "pyRevit Core Tools"; Types: full compact custom; Flags: fixed
Name: "ext"; Description: "pyRevit Extended Extensions"; Types: full custom
Name: "dev"; Description: "pyRevit Developer Extensions"; Types: custom
Name: "learn"; Description: "pyRevit Tutorials Extension"; Types: custom

[Files]
; bin\
Source: "..\bin\*"; DestDir: "{app}\bin"; Flags: ignoreversion recursesubdirs; Components: core dev learn
; extensions
Source: "..\extensions\*"; DestDir: "{app}\extensions"; Flags: ignoreversion; Components: core dev learn
Source: "..\extensions\pyRevitCore.extension\*"; DestDir: "{app}\extensions\pyRevitCore.extension"; Flags: ignoreversion recursesubdirs; Components: core
Source: "..\extensions\pyRevitTools.extension\*"; DestDir: "{app}\extensions\pyRevitTools.extension"; Flags: ignoreversion recursesubdirs; Components: core
Source: "..\extensions\pyRevitTags.extension\*"; DestDir: "{app}\extensions\pyRevitTags.extension"; Flags: ignoreversion recursesubdirs; Components: ext
Source: "..\extensions\pyRevitTemplates.extension\*"; DestDir: "{app}\extensions\pyRevitTemplates.extension"; Flags: ignoreversion recursesubdirs; Components: ext
Source: "..\extensions\pyRevitDevTools.extension\*"; DestDir: "{app}\extensions\pyRevitDevTools.extension"; Flags: ignoreversion recursesubdirs; Components: dev
Source: "..\extensions\pyRevitDevHooks.extension\*"; DestDir: "{app}\extensions\pyRevitDevHooks.extension"; Flags: ignoreversion recursesubdirs; Components: dev
Source: "..\extensions\pyRevitTutor.extension\*"; DestDir: "{app}\extensions\pyRevitTutor.extension"; Flags: ignoreversion recursesubdirs; Components: learn
Source: "..\extensions\pyRevitBundlesCreatorExtension.extension\*"; DestDir: "{app}\extensions\pyRevitBundlesCreatorExtension.extension"; Flags: ignoreversion recursesubdirs; Components: ext
; python libs
Source: "..\pyrevitlib\*"; DestDir: "{app}\pyrevitlib"; Flags: ignoreversion recursesubdirs; Components: core dev learn
; python site_packages
Source: "..\site-packages\*"; DestDir: "{app}\site-packages"; Flags: ignoreversion recursesubdirs; Components: core dev learn
; clone arguments
Source: "..\release\.pyrevitargs"; DestDir: "{app}"; Flags: ignoreversion; Components: core dev learn
Source: "..\pyRevitfile"; DestDir: "{app}"; Flags: ignoreversion; Components: core dev learn

[Run]
Filename: "{app}\bin\pyrevit.exe"; Description: "Clearing caches..."; Parameters: "caches clear --all"; Flags: runhidden; Check: not IsAdmin
Filename: "{app}\bin\pyrevit.exe"; Description: "Detach existing clones..."; Parameters: "detach --all"; Flags: runhidden; Check: not IsAdmin
Filename: "{app}\bin\pyrevit.exe"; Description: "Registering this clone..."; Parameters: "clones add this master --force"; Flags: runhidden; Check: not IsAdmin
Filename: "{app}\bin\pyrevit.exe"; Description: "Attaching this clone..."; Parameters: "attach master default --installed"; Flags: runhidden; Check: not IsAdmin
Filename: "{app}\bin\pyrevit.exe"; Description: "Seeding extension defaults..."; Parameters: "configs seedshippeddefaults"; Flags: runhidden; Check: not IsAdmin

[UninstallRun]
Filename: "{app}\bin\pyrevit.exe"; RunOnceId: "ClearCaches"; Parameters: "caches clear --all"; Flags: runhidden
Filename: "{app}\bin\pyrevit.exe"; RunOnceId: "DetachClones"; Parameters: "detach --all"; Flags: runhidden
Filename: "{app}\bin\pyrevit.exe"; RunOnceId: "RemoveMcpServers"; Parameters: "mcp uninstall --all --owned"; Flags: runhidden

[Code]
function RunPyRevitCommand(const Params: String): Boolean;
var
  ResultCode: Integer;
  PyRevitExe: String;
begin
  Result := False;
  PyRevitExe := ExpandConstant('{app}\bin\pyrevit.exe');
  if not FileExists(PyRevitExe) then
  begin
    Log('pyrevit.exe not found: ' + PyRevitExe);
    Exit;
  end;
  Result := ExecAsOriginalUser(PyRevitExe, Params, ExpandConstant('{app}\bin'), SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if not Result then
    Log('Failed to execute pyrevit ' + Params)
  else if ResultCode <> 0 then
  begin
    Log('pyrevit exited with code ' + IntToStr(ResultCode) + ': ' + Params);
    Result := False;
  end;
end;

procedure RunElevatedUserPostInstallCommands;
begin
  RunPyRevitCommand('caches clear --all');
  RunPyRevitCommand('detach --all');
  if not RunPyRevitCommand('clones add this master --force') then
    Log('Elevated install: pyrevit clones add failed for original user');
  if not RunPyRevitCommand('attach master default --installed') then
    Log('Elevated install: pyrevit attach failed for original user');
  if not RunPyRevitCommand('configs seedshippeddefaults') then
    Log('Elevated install: pyrevit configs seedshippeddefaults failed for original user');
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not RunPyRevitCommand('env path ensure "' + ExpandConstant('{app}\bin') + '" --scope=user') then
      MsgBox(
        'pyRevit was installed, but the installer could not register the install folder in your user PATH environment variable.' + #13#10 + #13#10 +
        'You may need to manually add the following folder to your user PATH:' + #13#10 +
        '  ' + ExpandConstant('{app}\bin'),
        mbError, MB_OK);
    if IsAdmin then
      RunElevatedUserPostInstallCommands;
  end;
end;

function InitializeSetup: Boolean;
begin
  // WebView2 Runtime for the output window renderer
  Dependency_AddWebView2;
  // .NET 8 for Revit 2025-2026
  Dependency_AddDotNet80;
  Dependency_AddDotNet80Desktop;
  // .NET 10 for Revit 2027+
  Dependency_AddDotNet100;
  Dependency_AddDotNet100Desktop;
  Result := True;
end;
