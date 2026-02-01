#define MyAppName "pyRevit CLI"
#define MyAppUUID "9557b432-cf79-4ece-91cf-b8f996c88b47"
#define MyAppVersion "6.0.0.26032"
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
AppCopyright=Copyright © 2014-2025 pyRevitLabs.io
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
; See dev/scripts/config.py INSTALLER_EXES
OutputBaseFilename=pyRevit_CLI_{#MyAppVersion}_signed
SetupIconFile=..\bin\pyrevit_cli.ico
Compression=lzma
SolidCompression=yes
DisableWelcomePage=no
WizardStyle=classic
WizardImageFile=.\pyrevit-cli.bmp
WizardSmallImageFile=.\pyrevit-banner.bmp
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; bin\
Source: "..\bin\*"; DestDir: "{app}\bin"; Flags: ignoreversion

[Registry]
; Uninstaller does not undo this change
; Multiple installs keep adding the path
; When run as admin, HKCU would be the elevated user's; PATH is set in CurStepChanged via ExecAsOriginalUser instead.
; https://stackoverflow.com/a/3431379/2350244
; https://stackoverflow.com/a/9962307/2350244 (mod path module)
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}\bin"; Check: NotAdminAndPathNotExists

[Run]
Filename: "{app}\bin\pyrevit.exe"; Description: "Clearning caches..."; Parameters: "caches clear --all"; Flags: runhidden
Filename: "{app}\bin\pyrevit.exe"; Description: "Detach existing clones..."; Parameters: "detach --all"; Flags: runhidden

[UninstallRun]
Filename: "{app}\bin\pyrevit.exe"; RunOnceId: "ClearCaches"; Parameters: "caches clear --all"; Flags: runhidden
Filename: "{app}\bin\pyrevit.exe"; RunOnceId: "DetachClones"; Parameters: "detach --all"; Flags: runhidden

[Code]
function NotAdminAndPathNotExists: Boolean;
var
  OrigPath: String;
  AppPath: String;
begin
  Result := not IsAdmin;
  if Result then
  begin
    AppPath := ExpandConstant('{app}\bin');
    if RegQueryStringValue(HKCU, 'Environment', 'Path', OrigPath) then
      Result := Pos(';' + Uppercase(AppPath) + ';', ';' + Uppercase(OrigPath) + ';') = 0;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Params: String;
  InstallPathEscaped: String;
  ResultCode: Integer;
begin
  if (CurStep = ssPostInstall) and IsAdmin then
  begin
    InstallPathEscaped := ExpandConstant('{app}\bin');
    StringChangeEx(InstallPathEscaped, '''', '''''', True);
    Params := '-NoProfile -ExecutionPolicy Bypass -Command "' +
      '$appPath = ''' + InstallPathEscaped + ''';' +
      '$userPath = [Environment]::GetEnvironmentVariable(''Path'', ''User'');' +
      'if ($userPath -notlike "' + '"*$appPath*"' + '") {' +
      '  [Environment]::SetEnvironmentVariable(''Path'', $userPath + '';'' + $appPath, ''User'')' +
      '}"';
    if ExecAsOriginalUser(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0) then
      Log('Added install path to original user PATH')
    else
    begin
      Log('ExecAsOriginalUser failed or non-zero exit when adding PATH');
      MsgBox('pyRevit CLI could not update your user PATH environment variable.' + #13#10 + #13#10 + 'You may need to add the install directory to PATH manually:' + #13#10 + '  ' + ExpandConstant('{app}\bin') + #13#10 + #13#10 + 'Alternatively, re-run this installer without elevation so PATH can be updated automatically.', mbError, MB_OK);
    end;
  end;
end;

function InitializeSetup: Boolean;
begin
  Dependency_AddDotNet80;
  Dependency_AddDotNet80Desktop;
  Result := True;
end;