#define MyAppName "pyRevit"
#define MyAppUUID "f2a3da53-6f34-41d5-abbd-389ffa7f4d5f"
#define MyAppVersion "6.5.3.26176"
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
DefaultDirName={autopf}\{#MyAppName}-Master
UsePreviousAppDir=yes
;     mode
PrivilegesRequired=admin
; Build info
OutputDir=..\dist
; See dev/scripts/config.py INSTALLER_EXES
OutputBaseFilename=pyRevit_{#MyAppVersion}_admin_signed
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

[Registry]
; Uninstaller does not undo this change
; Multiple installs keep adding the path
; https://stackoverflow.com/a/3431379/2350244
; https://stackoverflow.com/a/9962307/2350244 (mod path module)
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}\bin"

[UninstallRun]
Filename: "{app}\bin\pyrevit.exe"; RunOnceId: "ClearCaches"; Parameters: "caches clear --all"; Flags: runhidden
Filename: "{app}\bin\pyrevit.exe"; RunOnceId: "DetachClones"; Parameters: "detach --all"; Flags: runhidden

[Code]
function RunPyRevitCommand(const Params: String; const AsOriginalUser: Boolean): Boolean;
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
  if AsOriginalUser then
    Result := ExecAsOriginalUser(PyRevitExe, Params, ExpandConstant('{app}\bin'), SW_HIDE, ewWaitUntilTerminated, ResultCode)
  else
    Result := Exec(PyRevitExe, Params, ExpandConstant('{app}\bin'), SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if not Result then
    Log('Failed to execute pyrevit ' + Params)
  else if ResultCode <> 0 then
  begin
    Log('pyrevit exited with code ' + IntToStr(ResultCode) + ': ' + Params);
    Result := False;
  end;
end;

procedure RunAdminPostInstallCommands;
begin
  RunPyRevitCommand('caches clear --all', True);
  RunPyRevitCommand('detach --all', True);
  if not RunPyRevitCommand('clones add this master --force', False) then
    MsgBox(
      'The pyRevit admin installer could not register the installed clone (pyrevit clones add).' + #13#10 + #13#10 +
      'Run the following from an elevated command prompt in the install bin folder:' + #13#10 +
      '  pyrevit clones add this master --force',
      mbError, MB_OK);
  if not RunPyRevitCommand('attach master default --installed --allusers', False) then
    MsgBox(
      'The pyRevit admin installer could not attach pyRevit to Revit for all users.' + #13#10 + #13#10 +
      'Run the following from an elevated command prompt in the install bin folder:' + #13#10 +
      '  pyrevit attach master default --installed --allusers',
      mbError, MB_OK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    RunAdminPostInstallCommands;
end;

function InitializeSetup: Boolean;
begin
  // .NET 8 for Revit 2025-2026
  Dependency_AddDotNet80;
  Dependency_AddDotNet80Desktop;
  // .NET 10 for Revit 2027+
  Dependency_AddDotNet100;
  Dependency_AddDotNet100Desktop;
  Result := True;
end;
