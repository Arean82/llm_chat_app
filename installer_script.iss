

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-1234567890AB}
AppName=LLM Chat App
AppVersion=6.5.0
AppPublisher=Arean Narrayan
DefaultDirName={commonpf}\LLM Chat App
DefaultGroupName=LLM Chat App
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=LLM_Chat_App_Setup_v6.5.0
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=resources\app_icon.ico
UninstallDisplayIcon={app}\LLM Chat App.exe
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
Name: "{commondesktop}\LLM Chat App"; Filename: "{app}\LLM Chat App.exe"; IconFilename: "{app}\LLM Chat App.exe"
; Create Start Menu Shortcut
Name: "{commonprograms}\LLM Chat App"; Filename: "{app}\LLM Chat App.exe"; IconFilename: "{app}\LLM Chat App.exe"

[Run]
; Optional: Let user launch the app immediately after installing
Filename: "{app}\LLM Chat App.exe"; Description: "Launch LLM Chat App"; Flags: nowait postinstall skipifsilent