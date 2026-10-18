#define MyAppName "pyRevit CLI"
#define MyAppUUID "9557b432-cf79-4ece-91cf-b8f996c88b47"
#define MyAppVersion "7.0.0.26278"
#define MyAppPublisher "pyRevitLabs"
#define MyAppURL "pyrevitlabs.io"
#define MyAppExeName "pyrevit.exe"
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
DefaultDirName={autopf}\{#MyAppName}
UsePreviousAppDir=yes
;     mode
PrivilegesRequired=lowest
; Build info
OutputDir=..\dist
; Keep this list aligned with the installer assets staged by build/.
OutputBaseFilename=pyRevit_CLI_{#MyAppVersion}_signed
SetupIconFile=..\release\bin-assets\pyrevit_cli.ico
Compression=lzma
SolidCompression=yes
DisableWelcomePage=no
WizardStyle=classic
WizardImageFile=.\pyrevit-cli.bmp
WizardSmallImageFile=.\pyrevit-banner.bmp
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; bin\
Source: "..\bin\*"; DestDir: "{app}\bin"; Flags: ignoreversion

[Run]
Filename: "{app}\bin\pyrevit.exe"; Description: "Clearing caches..."; Parameters: "caches clear --all"; Flags: runhidden; Check: not IsAdmin
Filename: "{app}\bin\pyrevit.exe"; Description: "Detach existing clones..."; Parameters: "detach --all"; Flags: runhidden; Check: not IsAdmin

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
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not RunPyRevitCommand('env path ensure "' + ExpandConstant('{app}\bin') + '" --scope=user') then
      SuppressibleMsgBox(
        'pyRevit CLI was installed, but the installer could not register the install folder in your user PATH environment variable.' + #13#10 + #13#10 +
        'You may need to manually add the following folder to your user PATH:' + #13#10 +
        '  ' + ExpandConstant('{app}\bin'),
        mbError, MB_OK, MB_OK);
    if IsAdmin then
      RunElevatedUserPostInstallCommands;
  end;
end;

function InitializeSetup: Boolean;
begin
  // WebView2 Runtime for the output window renderer
  Dependency_AddWebView2;
  Dependency_AddDotNet80;
  Dependency_AddDotNet80Desktop;
  Result := True;
end;
