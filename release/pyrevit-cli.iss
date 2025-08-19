#define MyAppName "pyRevit CLI"
#define MyAppUUID "9557b432-cf79-4ece-91cf-b8f996c88b47"
#define MyAppVersion "5.1.0.25094"
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
AppCopyright=Copyright © 2014-2025 pyRevitLabs.io
LicenseFile=..\LICENSE.txt
; Installer
DefaultGroupName={#MyAppName}
DisableDirPage=auto
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

[Code]
const
    REQUIRED_MAJOR_VERSION = 8;

function CheckForDotNetRuntime(Path: String; var FoundVersion: String): Boolean;
var
    FindRec: TFindRec;
    Version: String;
    Major: Integer;
    SeparatorPos: Integer;
begin
    Result := False;
    if DirExists(Path) then
    begin
        if FindFirst(Path + '\*', FindRec) then
        begin
            try
                repeat
                    if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY <> 0) and (FindRec.Name <> '.') and (FindRec.Name <> '..') then
                    begin
                        Version := FindRec.Name;
                        SeparatorPos := Pos('.', Version);
                        if SeparatorPos > 0 then
                        begin
                            try
                                Major := StrToInt(Copy(Version, 1, SeparatorPos - 1));
                                if Major >= REQUIRED_MAJOR_VERSION then
                                begin
                                    FoundVersion := Version;
                                    Result := True;
                                    Exit;
                                end;
                            except
                            end;
                        end;
                    end;
                until not FindNext(FindRec);
            finally
                FindClose(FindRec);
            end;
        end;
    end;
end;

procedure GetDotNetDesktopRuntimeInfo(var Found: Boolean; var Version: String; var Path: String);
var
    PathX64, PathX86: String;
begin
    PathX64 := ExpandConstant('{pf64}\dotnet\shared\Microsoft.WindowsDesktop.App');
    PathX86 := ExpandConstant('{pf32}\dotnet\shared\Microsoft.WindowsDesktop.App');

    Found := CheckForDotNetRuntime(PathX64, Version);
    if Found then
    begin
      Path := PathX64;
      Exit;
    end;

    Found := CheckForDotNetRuntime(PathX86, Version);
    if Found then
    begin
      Path := PathX86;
      Exit;
    end;
end;

procedure InitializeWizard();
var
    IsInstalled: Boolean;
    FoundVersion, FoundPath: String;
begin
    GetDotNetDesktopRuntimeInfo(IsInstalled, FoundVersion, FoundPath);
    if IsInstalled then
    begin
        MsgBox('Found compatible .NET Desktop Runtime.'#13#10#13#10'Version: ' + FoundVersion + #13#10'Path: ' + FoundPath, mbInformation, MB_OK);
    end
    else
    begin
        MsgBox('Could not find .NET 8 Desktop Runtime.', mbError, MB_OK);
    end;
end;