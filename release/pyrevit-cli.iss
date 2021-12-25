#define MyAppName "pyRevit CLI"
#define MyAppUUID "5d419b28-c737-4fd3-9c33-6da59628a443"
#define MyAppVersion "4.8.9.21359+1855"
#define MyAppPublisher "pyRevitLabs"
#define MyAppURL "pyrevitlabs.io"
#define MyAppExeName "pyrevit.exe"

[Setup]
; App information
AppId={#MyAppUUID}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright=Copyright (C) 2014-2019 pyRevitLabs.io
LicenseFile=..\LICENSE.txt
; Installer
DefaultGroupName={#MyAppName}
DisableStartupPrompt=yes
DisableProgramGroupPage=yes
ArchitecturesInstallIn64BitMode=x64
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

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; bin\
Source: "..\bin\*"; DestDir: "{app}\bin"; Flags: ignoreversion

[Registry]
; Uninstaller does not undo this change
; Multiple installs keep adding the path
; https://stackoverflow.com/a/3431379/2350244
; https://stackoverflow.com/a/9962307/2350244 (mod path module)
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}\bin"

[Run]
Filename: "{app}\bin\pyrevit.exe"; Description: "Clearning caches..."; Parameters: "caches clear --all"; Flags: runhidden
Filename: "{app}\bin\pyrevit.exe"; Description: "Detach existing clones..."; Parameters: "detach --all"; Flags: runhidden

[UninstallRun]
Filename: "{app}\bin\pyrevit.exe"; RunOnceId: "ClearCaches"; Parameters: "caches clear --all"; Flags: runhidden
Filename: "{app}\bin\pyrevit.exe"; RunOnceId: "DetachClones"; Parameters: "detach --all"; Flags: runhidden