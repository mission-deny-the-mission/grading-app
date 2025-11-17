; Inno Setup Installer Script for Grading App
; This script creates a Windows installer for the Grading App desktop application.
;
; Prerequisites:
;   - Inno Setup 6.0 or later (https://jrsoftware.org/isinfo.php)
;   - PyInstaller build completed (dist/GradingApp/ directory must exist)
;
; Usage:
;   1. Build the application with PyInstaller:
;      pyinstaller grading-app.spec
;   2. Compile this script with Inno Setup Compiler:
;      iscc installer.iss
;   3. Output installer will be in: desktop/installer/windows/Output/GradingApp-Setup.exe

#define MyAppName "Grading App"
#define MyAppVersion GetVersionNumbersString("..\..\..\..\dist\GradingApp\GradingApp.exe")
#define MyAppPublisher "Grading App Team"
#define MyAppURL "https://github.com/yourusername/grading-app"
#define MyAppExeName "GradingApp.exe"
#define MyAppSourceDir "..\..\..\..\dist\GradingApp"

[Setup]
; Application metadata
AppId={{A1B2C3D4-E5F6-4G7H-8I9J-0K1L2M3N4O5P}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; Installation paths
DefaultDirName={autopf}\GradingApp
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; User data directory (preserved on uninstall)
; This is set via environment variable at runtime, not during install

; Output settings
OutputDir=Output
OutputBaseFilename=GradingApp-Setup
Compression=lzma2/max
SolidCompression=yes

; UI settings
WizardStyle=modern
SetupIconFile={#MyAppSourceDir}\{#MyAppExeName}
UninstallDisplayIcon={app}\{#MyAppExeName}

; Privileges
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Architecture
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Misc
AllowNoIcons=yes
LicenseFile=..\..\..\LICENSE.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Copy all files from PyInstaller dist directory
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
; Start Menu shortcut
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop shortcut (optional, selected via Tasks)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; Quick Launch shortcut (optional, for Windows XP/Vista/7)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
; Add uninstall information to Windows Registry
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{A1B2C3D4-E5F6-4G7H-8I9J-0K1L2M3N4O5P}_is1"; ValueType: string; ValueName: "DisplayName"; ValueData: "{#MyAppName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{A1B2C3D4-E5F6-4G7H-8I9J-0K1L2M3N4O5P}_is1"; ValueType: string; ValueName: "DisplayVersion"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{A1B2C3D4-E5F6-4G7H-8I9J-0K1L2M3N4O5P}_is1"; ValueType: string; ValueName: "Publisher"; ValueData: "{#MyAppPublisher}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{A1B2C3D4-E5F6-4G7H-8I9J-0K1L2M3N4O5P}_is1"; ValueType: string; ValueName: "URLInfoAbout"; ValueData: "{#MyAppURL}"; Flags: uninsdeletekey

[Run]
; Offer to launch application after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; No special uninstall cleanup needed - user data is preserved in %APPDATA%

[Code]
// Check for .NET Framework requirement (if needed in future)
// Currently not required, but included as placeholder for future dependencies
function InitializeSetup(): Boolean;
begin
  Result := True;
  // Add dependency checks here if needed
  // Example: Check for .NET Framework, Visual C++ Redistributable, etc.
end;

// Custom message when user data will be preserved
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  UserDataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    UserDataDir := ExpandConstant('{userappdata}\GradingApp');
    if DirExists(UserDataDir) then
    begin
      MsgBox('Your user data has been preserved at:' + #13#10 +
             UserDataDir + #13#10#13#10 +
             'This includes your database, uploads, and settings.' + #13#10 +
             'Delete this folder manually if you want to remove all data.',
             mbInformation, MB_OK);
    end;
  end;
end;
