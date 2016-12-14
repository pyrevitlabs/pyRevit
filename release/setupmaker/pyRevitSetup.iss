#define MyAppName "pyRevit"
#define MyAppVersion "-v3beta"
#define MyAppPublisher "Ehsan Iran-Nejad"
#define MyAppURL "http://eirannejad.github.io/pyRevit/"

[Setup]
SourceDir=Z:\Revit API\pyrevitdev\__misc__\setup

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
AppCopyright=Copyright (C) 2014-2016 Ehsan Iran-Nejad
DisableWelcomePage=no
WizardImageFile=installerimage.bmp
LicenseFile=LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "PortableGit*.exe"; DestDir: "{app}"; Flags: ignoreversion deleteafterinstall
Source: "makeaddins.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "removeaddins.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "removeold.bat"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{userappdata}\{#MyAppName}"

[InstallDelete]
Type: filesandordirs; Name: "{app}\__git__"
Type: filesandordirs; Name: "{app}\__init__"
Type: filesandordirs; Name: "{app}\pyRevit"

[Run]
Filename: "{app}\removeold.bat"; StatusMsg: "Cleaning up older versions..."; Flags: runhidden
Filename: "{app}\PortableGit-2.10.0-64-bit.7z.exe"; Parameters: "-y -gm2 -InstallPath=""{app}\\__git__\\"""; StatusMsg: "Installing portable git. This might take a few minutes..."; Flags: runhidden
Filename: "{app}\__git__\cmd\git.exe"; Parameters: "clone -b loader --single-branch ""https://github.com/eirannejad/pyRevit"" ""{app}\__init__"""; StatusMsg: "Cloning pyRevit loader from github. This might take a few minutes..."; Flags: runhidden
Filename: "{app}\__git__\cmd\git.exe"; Parameters: "clone -b verThreeDev --single-branch ""https://github.com/eirannejad/pyRevit"" ""{app}\pyRevit"""; StatusMsg: "Cloning pyRevit from github. This might take a few minutes..."; Flags: runhidden
Filename: "{app}\makeaddins.bat"; Parameters: """{app}\__init__\RevitPythonLoader.dll"""; StatusMsg: "Creating Addin files for currently installed Revit versions..."; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[UninstallRun]
Filename: "{app}\removeaddins.bat";

[Code]
function InitializeSetup(): Boolean;
var
  WinHttpReq: Variant;
  Connected: Boolean;
begin
  Connected := False;
  repeat
    Log('Checking connection to the server');
    try
      WinHttpReq := CreateOleObject('WinHttp.WinHttpRequest.5.1');
      { Use your real server host name }
      WinHttpReq.Open('GET', 'http://www.github.com/', False);
      WinHttpReq.Send('');
      Log('Connected to the github servers; status: ' + IntToStr(WinHttpReq.Status) + ' ' + WinHttpReq.StatusText);
      Connected := True;
    except
      Log('Error connecting to the github servers: ' + GetExceptionMessage);
      if WizardSilent then
      begin
        Log('Connection to the github servers is not available, aborting silent installation');
        Result := False;
        Exit;
      end
        else
      if MsgBox('Cannot reach github servers. Please check your Internet connection.', mbError, MB_RETRYCANCEL) = IDRETRY then
      begin
        Log('Retrying');
      end
        else
      begin
        Log('Aborting');
        Result := False;
        Exit;
      end;
    end;
  until Connected;

  Result := True;
end;