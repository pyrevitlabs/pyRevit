#define MyAppName "pyRevit"
#define MyAppVersion "v45"
#define MyAppPublisher "Ehsan Iran-Nejad"
#define MyAppURL "http://eirannejad.github.io/pyRevit/"
#define MyAppGit "https://github.com/eirannejad/pyRevit.git"

[Setup]
AppId={{A31B9631-12A5-476E-BFDA-239E283F5D43}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName}-{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={userappdata}\{#MyAppName}\{#MyAppName}-{#MyAppVersion}
DisableProgramGroupPage=yes
OutputBaseFilename={#MyAppName}Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
SetupIconFile={#MyAppName}.ico
;UninstallDisplayIcon={#MyAppName}.ico
AppCopyright=Copyright (c) 2014-2018 {#MyAppPublisher}
;Allow install by any user class. See pyRevit PR #262
;PrivilegesRequired=lowest
DisableWelcomePage=no
WizardImageFile={#MyAppName}1.bmp
WizardSmallImageFile={#MyAppName}2.bmp
LicenseFile=..\..\LICENSE.TXT
; http://www.jrsoftware.org/ishelp/index.php?topic=setup_changesenvironment
ChangesEnvironment=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\..\bin\*"; DestDir: "{tmp}\pyRevit"; Flags: recursesubdirs createallsubdirs

[InstallDelete]
Type: filesandordirs; Name: "{app}\pyRevit"

[Icons]
Name: "{group}\Update pyRevit"; Filename: "{app}\pyRevit\bin\pyrevit.exe"; Parameters: "update --all"

[Run]
Filename: "{tmp}\pyRevit\pyrevit.exe"; Parameters:"install {#MyAppGit} --branch master {app}\pyRevit"; StatusMsg: "Cloning pyRevit repository from Github...This might take a while..."; Flags: runhidden
;Filename: "{tmp}\pyRevit\pyrevit.exe"; Parameters:"detach --all"; StatusMsg: "Cleaning up older versions..."; Flags: runhidden
;Filename: "{tmp}\pyRevit\pyrevit.exe"; Parameters:"attach --all {code:GetAllUsersState}"; StatusMsg: "Creating Addin files for currently installed Revit versions..."; Flags: runhidden
Filename: "{app}\pyRevit\release\uninstall_addin.bat"; StatusMsg: "Cleaning up older versions..."; Flags: runhidden
Filename: "{app}\pyRevit\release\install_addin.bat";  Parameters:"{code:GetAllUsersState}"; StatusMsg: "Creating Addin files for currently installed Revit versions..."; Flags: runhidden


[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[UninstallRun]
;Filename: "{tmp}\pyrevit.exe"; Parameters:"detach --all"; Flags: runhidden
Filename: "{app}\pyRevit\release\uninstall_addin.bat";

[Code]
var
  UsagePage: TInputOptionWizardPage;
  VersionPage: TInputOptionWizardPage;

procedure InitializeWizard;
begin
  { Create the user mode page }
  UsagePage := CreateInputOptionPage(wpLicense,
    'Select Installation Type', 'For Current user or All users?',
    'Please specify how you would like to install pyRevit, then click Next.', True, False);
  UsagePage.Add('Current User Only');
  UsagePage.Add('All Users (pyRevit will load for all users)');
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
  Result := True;
  if WizardSilent <> True then
    begin
      if CurPageID = UsagePage.ID then
        begin
          if UsagePage.Values[1] = True then
            WizardForm.DirEdit.Text := ExpandConstant('{commonappdata}') + '\{#MyAppName}\{#MyAppName}{#MyAppVersion}'
          else
            WizardForm.DirEdit.Text := ExpandConstant('{userappdata}') + '\{#MyAppName}\{#MyAppName}{#MyAppVersion}';
        end;
    end;
end;
