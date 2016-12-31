#define MyAppName "pyRevit"
#define MyAppVersion "-v4"
#define MyAppPublisher "Ehsan Iran-Nejad"
#define MyAppURL "http://eirannejad.github.io/pyRevit/"

[Setup]
AppId={{B93A3916-AE34-493F-984E-6D02E492D328}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={userappdata}\{#MyAppName}\{#MyAppName}{#MyAppVersion}
DisableProgramGroupPage=yes
OutputBaseFilename={#MyAppName}Setup{#MyAppVersion}
Compression=lzma
SolidCompression=yes
SetupIconFile={#MyAppName}Setup.ico
AppCopyright=Copyright (c) 2014-2017 Ehsan Iran-Nejad
DisableWelcomePage=no
WizardImageFile=installerimage.bmp
LicenseFile=LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\..\*"; DestDir: "{app}\"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\.git\*"; DestDir: "{app}\.git"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\.idea\*"; DestDir: "{app}\.idea"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\.gitignore"; DestDir: "{app}\"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\.gitattributes"; DestDir: "{app}\"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{userappdata}\{#MyAppName}"

[InstallDelete]
Type: filesandordirs; Name: "{app}\pyRevit"

[Run]
Filename: "{app}\release\uninstall_addin.bat"; StatusMsg: "Cleaning up older versions..."; Flags: runhidden
Filename: "{app}\release\install_addin.bat"; StatusMsg: "Creating Addin files for currently installed Revit versions..."; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[UninstallRun]
Filename: "{app}\release\uninstall_addin.bat";