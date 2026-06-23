#define MyAppName "pyRevit"
#define MyAppUUID "f2a3da53-6f34-41d5-abbd-389ffa7f4d5f"
#define MyAppVersion "6.5.0.26173"
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
function CreateInstallAllUsersMarker: Boolean;
var
  ProgramDataPyRevit: String;
  MarkerPath: String;
begin
  Result := False;
  ProgramDataPyRevit := ExpandConstant('{commonappdata}\pyRevit');
  MarkerPath := ProgramDataPyRevit + '\install_all_users';
  if ForceDirectories(ProgramDataPyRevit) then
  begin
    if SaveStringToFile(MarkerPath, 'AllUsers', False) then
    begin
      Log('Created install_all_users marker at: ' + MarkerPath);
      Result := True;
    end
    else
      Log('Could not write install_all_users marker: ' + MarkerPath);
  end
  else
  begin
    Log('Could not create ProgramData\pyRevit for install_all_users marker');
    MsgBox('Warning: Could not create all-users marker file. Config will use per-user scope.', mbInformation, MB_OK);
  end;
end;

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
    Log('pyrevit exited with code ' + IntToStr(ResultCode) + ': ' + Params);
end;

procedure RunAdminPostInstallCommands;
begin
  if not CreateInstallAllUsersMarker then
    Log('Continuing post-install without all-users marker; clone registry may use per-user config.');

  RunPyRevitCommand('caches clear --all', True);
  RunPyRevitCommand('detach --all', True);
  RunPyRevitCommand('clones add this master --force', False);
  RunPyRevitCommand('attach master default --installed --allusers', False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    RunAdminPostInstallCommands;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  MarkerPath: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    MarkerPath := ExpandConstant('{commonappdata}\pyRevit\install_all_users');
    if FileExists(MarkerPath) and DeleteFile(MarkerPath) then
      Log('Removed install_all_users marker')
    else if FileExists(MarkerPath) then
      Log('Could not remove install_all_users marker: ' + MarkerPath);
  end;
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
