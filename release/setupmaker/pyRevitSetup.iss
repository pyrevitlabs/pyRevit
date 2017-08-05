#define MyAppName "pyRevit"
#define MyAppVersion "-v4"
#define MyAppPublisher "Ehsan Iran-Nejad"
#define MyAppURL "http://eirannejad.github.io/pyRevit/"
#define MyAppGit "https://github.com/eirannejad/pyRevit.git"

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
Source: "..\..\release\pyRevitCloner\pyRevitCloner\bin\Release\*"; DestDir: "{tmp}\"; Flags: recursesubdirs createallsubdirs

[InstallDelete]
Type: filesandordirs; Name: "{app}\pyRevit"

[Run]
Filename: "{tmp}\pyRevitCloner.exe"; Parameters:"{#MyAppGit} {app}\pyRevit"; StatusMsg: "Cloning pyRevit repository from Github...This might take a while..."; Flags: runhidden
Filename: "{app}\pyRevit\release\uninstall_addin.bat"; StatusMsg: "Cleaning up older versions..."; Flags: runhidden
Filename: "{app}\pyRevit\release\install_addin.bat"; Parameters:"{code:GetAllUsersState}"; StatusMsg: "Creating Addin files for currently installed Revit versions..."; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[UninstallRun]
Filename: "{app}\pyRevit\release\uninstall_addin.bat";

[Code]
var
  UsagePage: TInputOptionWizardPage;

procedure InitializeWizard;
begin
  { Create the pages }  
  UsagePage := CreateInputOptionPage(wpLicense,
    'Select Installation Type', 'For Current user or All users?',
    'Please specify how you would like to install pyRevit, then click Next.',
    True, False);
  UsagePage.Add('Current User Only');
  UsagePage.Add('All Users (pyRevit will load for all users)');
  
  { Set default values}
  UsagePage.Values[0] := True;
  UsagePage.Values[0] := False;
end;

function GetAllUsersState(Param: string): String;
begin
  { Return the selected user level }
  if UsagePage.Values[1] = True then
      Result := '--allusers';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  { Validate certain pages before allowing the user to proceed }
  if CurPageID = UsagePage.ID then
    begin
      if UsagePage.Values[1] = True then
        WizardForm.DirEdit.Text := ExpandConstant('{commonappdata}') + '\{#MyAppName}'
      else
        WizardForm.DirEdit.Text := ExpandConstant('{userappdata}') + '\{#MyAppName}'
    end;
  
  Result := True;
end;