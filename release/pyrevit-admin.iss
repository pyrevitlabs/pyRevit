#define MyAppName "pyRevit"
#define MyAppUUID "f2a3da53-6f34-41d5-abbd-389ffa7f4d5f"
#define MyAppVersion "5.2.0.25181"
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
DefaultDirName={autopf}\{#MyAppName}-Master
UsePreviousAppDir=yes
;     mode
PrivilegesRequired=admin
; Build info
OutputDir=..\dist
; See dev/scripts/config.py INSTALLER_EXES
OutputBaseFilename=pyRevit_{#MyAppVersion}_admin_signed
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
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}\bin"

[Run]
Filename: "{app}\bin\pyrevit.exe"; Description: "Clearning caches..."; Parameters: "caches clear --all"; Flags: runhidden runascurrentuser
Filename: "{app}\bin\pyrevit.exe"; Description: "Detach existing clones..."; Parameters: "detach --all"; Flags: runhidden runascurrentuser
Filename: "{app}\bin\pyrevit.exe"; Description: "Registering this clone..."; Parameters: "clones add this master --force"; Flags: runhidden runascurrentuser
Filename: "{app}\bin\pyrevit.exe"; Description: "Attaching this clone..."; Parameters: "attach master default --installed"; Flags: runhidden runascurrentuser

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
        try
            Result := StrToInt(MajorStr);
        except
            Result := 0; // Invalid version
        end;
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
