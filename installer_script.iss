

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-1234567890AB}
AppName=Synora Studio
AppVersion=9.0.0
AppPublisher=Arean Narrayan
DefaultDirName={commonpf}\Synora Studio
DefaultGroupName=Synora Studio
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=Synora_Studio_Setup_v9.0.0
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=resources\app_icon.ico
UninstallDisplayIcon={app}\Synora Studio.exe
WizardStyle=modern
PrivilegesRequired=admin
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[InstallDelete]
; Clean up old UI files to ensure a fresh sync
Type: filesandordirs; Name: "{app}\ui_designer"

[Files]
; Grab EVERYTHING inside the dist folder (exe, _internal folder, etc.)
Source: "dist\LLM_Chat_dir\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Create Desktop Shortcut
Name: "{commondesktop}\Synora Studio"; Filename: "{app}\Synora Studio.exe"; IconFilename: "{app}\Synora Studio.exe"
; Create Start Menu Shortcut
Name: "{commonprograms}\Synora Studio"; Filename: "{app}\Synora Studio.exe"; IconFilename: "{app}\Synora Studio.exe"

[Run]
; Optional: Let user launch the app immediately after installing
Filename: "{app}\Synora Studio.exe"; Description: "Launch Synora Studio"; Flags: nowait postinstall skipifsilent