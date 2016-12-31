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
Source: "..\..\.git\*"; DestDir: "{app}\.git"; Flags: ignoreversion recursesubdirs
Source: "..\..\extensions\*"; DestDir: "{app}\extensions"; Flags: ignoreversion recursesubdirs
Source: "..\..\lib\*"; DestDir: "{app}\lib"; Flags: ignoreversion recursesubdirs
Source: "..\..\release\*"; DestDir: "{app}\release"; Flags: ignoreversion recursesubdirs
Source: "..\..\.gitattributes"; DestDir: "{app}"
Source: "..\..\.gitignore"; DestDir: "{app}"
Source: "..\..\README.md"; DestDir: "{app}"

[Dirs]
Name: "{userappdata}\{#MyAppName}"

[InstallDelete]
Type: filesandordirs; Name: "{app}\pyRevit"

[Run]
Filename: "{app}\release\setupmaker\removeold.bat"; StatusMsg: "Cleaning up older versions..."; Flags: runhidden
Filename: "{app}\release\setupmaker\makeaddins.bat"; Parameters: """{app}\lib\pyrevit\loader\addin\pyRevitLoader.dll"""; StatusMsg: "Creating Addin files for currently installed Revit versions..."; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[UninstallRun]
Filename: "{app}\release\setupmaker\removeaddins.bat";