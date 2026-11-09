; Inno Setup script: per-user Windows x64 installer for Cockpit (no admin rights needed).
; Build with:  ISCC /DAppVersion=0.1.0 desktop\installer.iss   (scripts\build-desktop.ps1 does it)
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{B6E3F0C2-6C0B-4E7E-9F38-6E2C8D2A7C11}
AppName=Cockpit
AppVersion={#AppVersion}
AppPublisher=Cockpit
DefaultDirName={autopf}\Cockpit
DefaultGroupName=Cockpit
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist-desktop
OutputBaseFilename=Cockpit-{#AppVersion}-windows-x64-setup
SetupIconFile=assets\cockpit.ico
UninstallDisplayIcon={app}\Cockpit.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\build\desktop\dist\Cockpit\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Cockpit"; Filename: "{app}\Cockpit.exe"
Name: "{autodesktop}\Cockpit"; Filename: "{app}\Cockpit.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Cockpit.exe"; Description: "Start Cockpit"; Flags: nowait postinstall skipifsilent
; Uninstalling removes the program only. Data stays in %APPDATA%\Cockpit.
