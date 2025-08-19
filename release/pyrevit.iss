#define MyAppName "pyRevit"
#define MyAppUUID "f2a3da53-6f34-41d5-abbd-389ffa7f4d5f"
#define MyAppVersion "5.1.0.25094"
#define MyAppPublisher "pyRevitLabs"
#define MyAppURL "pyrevitlabs.io"

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
DefaultDirName={userappdata}\{#MyAppName}-Master
UsePreviousAppDir=yes
;     mode
PrivilegesRequired=lowest
; Build info
OutputDir=..\dist
; See dev/scripts/config.py INSTALLER_EXES
OutputBaseFilename=pyRevit_{#MyAppVersion}_signed
SetupIconFile=..\bin\pyrevit.ico
Compression=lzma
SolidCompression=yes
DisableWelcomePage=no
WizardStyle=classic
WizardImageFile=.\pyrevit.bmp
WizardSmallImageFile=.\pyrevit-banner.bmp

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Components]
Name: "core"; Description: "pyRevit Core Tools"; Types: full compact custom; Flags: fixed
Name: "ext"; Description: "pyRevit Extended Extensions"; Types: full custom
Name: "dev"; Description: "pyRevit Developer Extensions"; Types: custom
Name: "learn"; Description: "pyRevit Tutorials Extension"; Types: custom

[Files]
; bin\
Source: "..\bin\*"; DestDir: "{app}\bin"; Flags: ignoreversion recursesubdirs; Components: core dev learn
; extensions
Source: "..\extensions\*"; DestDir: "{app}\extensions"; Flags: ignoreversion; Components: core dev learn
Source: "..\extensions\pyRevitCore.extension\*"; DestDir: "{app}\extensions\pyRevitCore.extension"; Flags: ignoreversion recursesubdirs; Components: core
Source: "..\extensions\pyRevitTools.extension\*"; DestDir: "{app}\extensions\pyRevitTools.extension"; Flags: ignoreversion recursesubdirs; Components: core
Source: "..\extensions\pyRevitTags.extension\*"; DestDir: "{app}\extensions\pyRevitTags.extension"; Flags: ignoreversion recursesubdirs; Components: ext
Source: "..\extensions\pyRevitTemplates.extension\*"; DestDir: "{app}\extensions\pyRevitTemplates.extension"; Flags: ignoreversion recursesubdirs; Components: ext
Source: "..\extensions\pyRevitDevTools.extension\*"; DestDir: "{app}\extensions\pyRevitDevTools.extension"; Flags: ignoreversion recursesubdirs; Components: dev
Source: "..\extensions\pyRevitDevHooks.extension\*"; DestDir: "{app}\extensions\pyRevitDevHooks.extension"; Flags: ignoreversion recursesubdirs; Components: dev
Source: "..\extensions\pyRevitTutor.extension\*"; DestDir: "{app}\extensions\pyRevitTutor.extension"; Flags: ignoreversion recursesubdirs; Components: learn
Source: "..\extensions\pyRevitBundlesCreatorExtension.extension\*"; DestDir: "{app}\extensions\pyRevitBundlesCreatorExtension.extension"; Flags: ignoreversion recursesubdirs; Components: ext
; python libs
Source: "..\pyrevitlib\*"; DestDir: "{app}\pyrevitlib"; Flags: ignoreversion recursesubdirs; Components: core dev learn
; python site_packages
Source: "..\site-packages\*"; DestDir: "{app}\site-packages"; Flags: ignoreversion recursesubdirs; Components: core dev learn
; clone arguments
Source: "..\release\.pyrevitargs"; DestDir: "{app}"; Flags: ignoreversion; Components: core dev learn
Source: "..\pyRevitfile"; DestDir: "{app}"; Flags: ignoreversion; Components: core dev learn

[Registry]
; Uninstaller does not undo this change
; Multiple installs keep adding the path
; https://stackoverflow.com/a/3431379/2350244
; https://stackoverflow.com/a/9962307/2350244 (mod path module)
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}\bin"

[Run]
Filename: "{app}\bin\pyrevit.exe"; Description: "Clearning caches..."; Parameters: "caches clear --all"; Flags: runhidden
Filename: "{app}\bin\pyrevit.exe"; Description: "Detach existing clones..."; Parameters: "detach --all"; Flags: runhidden
Filename: "{app}\bin\pyrevit.exe"; Description: "Registering this clone..."; Parameters: "clones add this master --force"; Flags: runhidden
Filename: "{app}\bin\pyrevit.exe"; Description: "Attaching this clone..."; Parameters: "attach master default --installed"; Flags: runhidden

[UninstallRun]
Filename: "{app}\bin\pyrevit.exe"; RunOnceId: "ClearCaches"; Parameters: "caches clear --all"; Flags: runhidden
Filename: "{app}\bin\pyrevit.exe"; RunOnceId: "DetachClones"; Parameters: "detach --all"; Flags: runhidden

[Code]
const
    REQUIRED_MAJOR_VERSION = 8;
    DOTNET_DESKTOP_RUNTIME_URL = 'https://dotnet.microsoft.com/en-us/download/dotnet/8.0';

function CheckForDotNetRuntime(Path: String): Boolean;
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

function IsDotNetDesktopRuntimeInstalled(): Boolean;
var
    PathX64, PathX86: String;
begin
    PathX64 := ExpandConstant('{pf64}\dotnet\shared\Microsoft.WindowsDesktop.App');
    PathX86 := ExpandConstant('{pf32}\dotnet\shared\Microsoft.WindowsDesktop.App');

    if CheckForDotNetRuntime(PathX64) then
    begin
        Result := True;
        Exit;
    end;

    if CheckForDotNetRuntime(PathX86) then
    begin
        Result := True;
        Exit;
    end;

    Result := False;
end;

function InitializeSetup(): Boolean;
var
    ErrorCode: Integer;
begin
    if IsDotNetDesktopRuntimeInstalled() then
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
