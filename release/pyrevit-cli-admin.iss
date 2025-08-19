#define MyAppName "pyRevit CLI"
#define MyAppUUID "9557b432-cf79-4ece-91cf-b8f996c88b47"
#define MyAppVersion "5.2.0.25181"
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
PrivilegesRequired=admin
; Build info
OutputDir=..\dist
; See dev/scripts/config.py INSTALLER_EXES
OutputBaseFilename=pyRevit_CLI_{#MyAppVersion}_admin_signed
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
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}\bin"

[Run]
Filename: "{app}\bin\pyrevit.exe"; Description: "Clearning caches..."; Parameters: "caches clear --all"; Flags: runhidden runascurrentuser
Filename: "{app}\bin\pyrevit.exe"; Description: "Detach existing clones..."; Parameters: "detach --all"; Flags: runhidden runascurrentuser

[UninstallRun]
Filename: "{app}\bin\pyrevit.exe"; RunOnceId: "ClearCaches"; Parameters: "caches clear --all"; Flags: runhidden runascurrentuser
Filename: "{app}\bin\pyrevit.exe"; RunOnceId: "DetachClones"; Parameters: "detach --all"; Flags: runhidden runascurrentuser

[Code]
const
    REQUIRED_MAJOR_VERSION = 8;

function GetMajorVersion(VersionStr: String): Integer;
var
    SeparatorPos, DashPos: Integer;
    MajorStr: String;
begin
    Result := 0;
    SeparatorPos := Pos('.', VersionStr);
    if SeparatorPos > 0 then
    begin
        MajorStr := Copy(VersionStr, 1, SeparatorPos - 1);
        // Handle preview/rc versions by checking for dash
        DashPos := Pos('-', MajorStr);
        if DashPos > 0 then
            MajorStr := Copy(MajorStr, 1, DashPos - 1);
        
        // Validate that MajorStr contains only digits
        if (Length(MajorStr) > 0) and (Length(MajorStr) <= 3) then
        begin
            try
                Result := StrToInt(MajorStr);
                // Additional validation: major version should be reasonable (1-99)
                if (Result < 1) or (Result > 99) then
                begin
                    Log('Warning: Invalid major version number: ' + MajorStr + ' from version: ' + VersionStr);
                    Result := 0;
                end;
            except
                on E: Exception do
                begin
                    Log('Error parsing major version from "' + MajorStr + '" in version "' + VersionStr + '": ' + E.Message);
                    Result := 0;
                end;
            end;
        end
        else
        begin
            Log('Warning: Invalid major version format: "' + MajorStr + '" from version: "' + VersionStr + '"');
            Result := 0;
        end;
    end
    else
    begin
        Log('Warning: No dot separator found in version string: "' + VersionStr + '"');
    end;
end;

function CheckForDotNetRuntime(Path: String; var FoundVersion: String): Boolean;
var
    FindRec: TFindRec;
    Version: String;
    Major: Integer;
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
                        Major := GetMajorVersion(Version);
                        if Major >= REQUIRED_MAJOR_VERSION then
                        begin
                            FoundVersion := Version;
                            Result := True;
                            Exit;
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
    MsgResult: Integer;
    ErrorCode: Integer;
begin
    GetDotNetDesktopRuntimeInfo(IsInstalled, FoundVersion, FoundPath);
    if not IsInstalled then
    begin
        MsgResult := MsgBox('Could not find .NET 8 Runtime.'#13#10#13#10'Click OK to download .NET 8 Runtime from Microsoft, or Cancel to abort installation.', mbError, MB_OKCANCEL);
        if MsgResult = IDOK then
        begin
            Exec('cmd', '/c start https://dotnet.microsoft.com/en-us/download/dotnet/8.0', '', SW_HIDE, ewNoWait, ErrorCode);
        end;
        Abort;
    end;
end;