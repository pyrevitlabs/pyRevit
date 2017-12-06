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
UninstallDisplayIcon={#MyAppName}Setup.ico
AppCopyright=Copyright (c) 2014-2017 Ehsan Iran-Nejad
;Allow install by any user class. See pyRevit PR #262
;PrivilegesRequired=lowest
DisableWelcomePage=no
WizardImageFile=installerimage.bmp
LicenseFile=LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\..\release\pyrevitgitservices\pyrevitgitservices\bin\Release\*"; DestDir: "{tmp}\"; Flags: recursesubdirs createallsubdirs

[InstallDelete]
Type: filesandordirs; Name: "{app}\pyRevit"

[Run]
Filename: "{tmp}\pyrevitgitservices.exe"; Parameters:"clone master {app}\pyRevit"; StatusMsg: "Cloning pyRevit repository from Github...This might take a while..."; Flags: runhidden
Filename: "{tmp}\pyrevitgitservices.exe"; Parameters:"setversion {app}\pyRevit {code:GetVersionHash}"; StatusMsg: "Setting repository version..."; Flags: runhidden
Filename: "{app}\pyRevit\release\uninstall_addin.bat"; StatusMsg: "Cleaning up older versions..."; Flags: runhidden
Filename: "{app}\pyRevit\release\install_addin.bat"; Parameters:"{code:GetAllUsersState}"; StatusMsg: "Creating Addin files for currently installed Revit versions..."; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[UninstallRun]
Filename: "{app}\pyRevit\release\uninstall_addin.bat";

[Code]
var
  UsagePage: TInputOptionWizardPage;
  VersionPage: TInputOptionWizardPage;
  CommitHashPage: TInputQueryWizardPage;

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

  { Create the user mode page }
  VersionPage := CreateInputOptionPage(wpSelectDir,
    'Select Installation Version', 'Do you want the latest pyRevit or a specific version?',
    'Please specify which version of pyRevit you want, then click Next.', True, False);
  VersionPage.Add('Install most recent pyRevit version (suggested)');
  VersionPage.Add('Install specific pyRevit version');
  VersionPage.Values[0] := True;
  VersionPage.Values[1] := False;

  { Create the version page }
  CommitHashPage := CreateInputQueryPage(VersionPage.ID,
    'Select pyRevit Version', '',
    'Please paste the full commit hash of the pyRevit version you like to install'
    + #13#10 + 'e.g: 2cae1da22b2f9eb1ac1f052d07e6be2961a9c591'
    + #13#10 + 'or just: 2cae1da');
  CommitHashPage.Add('Git Commit Hash Value', False);
  CommitHashPage.Values[0] := '';
end;

function GetAllUsersState(Param: string): String;
begin
  { Return the selected user level }
  if UsagePage.Values[1] = True then
      Result := '--allusers';
end;

function GetVersionHash(Param: string): String;
begin
  { Return the selected commit hash to be installed }
  Result := CommitHashPage.Values[0];
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  { initialize result to not skip any page (not necessary, but safer) }
  Result := False;
  { if the page that is asked to be skipped is your custom page, then... }
  if (PageID = CommitHashPage.ID) AND (VersionPage.Values[0] = True) then
    Result := True;
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
