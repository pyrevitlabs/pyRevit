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
    DOTNET_DESKTOP_RUNTIME_URL = 'https://dotnet.microsoft.com/en-us/download/dotnet/8.0';

function GetDotNetDesktopRuntimeVersion(var Major, Minor, Patch: Integer): Boolean;
var
    Path: String;
    FindRec: TFindRec;
    Version, MajorStr, MinorStr, PatchStr: String;
    SeparatorPos: Integer;
begin
    Result := False;
    Path := ExpandConstant('{autopf64}\dotnet\shared\Microsoft.WindowsDesktop.App');
    if not DirExists(Path) then
    begin
        Path := ExpandConstant('{autopf}\dotnet\shared\Microsoft.WindowsDesktop.App');
        if not DirExists(Path) then
            Exit;
    end;

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
                        MajorStr := Copy(Version, 1, SeparatorPos - 1);
                        Delete(Version, 1, SeparatorPos);
                        SeparatorPos := Pos('.', Version);
                        if SeparatorPos > 0 then
                        begin
                            MinorStr := Copy(Version, 1, SeparatorPos - 1);
                            PatchStr := Copy(Version, SeparatorPos + 1, Length(Version));
                            Major := StrToInt(MajorStr);
                            Minor := StrToInt(MinorStr);
                            Patch := StrToInt(PatchStr);
                            if Major > REQUIRED_MAJOR_VERSION then
                            begin
                                Result := True;
                                Exit;
                            end
                            else if Major = REQUIRED_MAJOR_VERSION then
                            begin
                                Result := True;
                            end;
                        end;
                    end;
                end;
            until not FindNext(FindRec);
        finally
            FindClose(FindRec);
        end;
    end;
end;

function InitializeSetup(): Boolean;
var
    Major, Minor, Patch: Integer;
begin
    if GetDotNetDesktopRuntimeVersion(Major, Minor, Patch) then
    begin
        Result := True;
    end
    else
    begin
        MsgBox('This application requires .NET ' + IntToStr(REQUIRED_MAJOR_VERSION) + ' Desktop Runtime or a later version. Please install it before running this setup.'#13#10'Click OK to open the download page.', mbError, MB_OK);
        ShellExec('open', DOTNET_DESKTOP_RUNTIME_URL, '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
        Result := False;
    end;
end;