; Inno Setup script for ReelGeek.
; Built by .github/workflows/build-windows.yml on a Windows runner.

#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

#define MyAppName     "ReelGeek"
#define MyAppPublisher "TechyGeeksHome"
#define MyAppURL      "https://techygeekshome.info/reelgeek/"
#define MyAppExeName  "ReelGeek.exe"

[Setup]
AppId={{7C1D4E52-9B3A-4F60-8E21-2A5C9D0F4B18}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=Output
OutputBaseFilename=ReelGeekSetup
SetupIconFile=reelgeek.ico
UninstallDisplayName={#MyAppName} {#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "..\dist\ReelGeek\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Open {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; The prepped-photo cache and settings live here. Leaving them behind after an
; uninstall would be litter, and they cost nothing to rebuild.
Type: filesandordirs; Name: "{localappdata}\ReelGeek"
