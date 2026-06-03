[Setup]
AppId={{2A3B4C5D-E6F7-8901-ABCD-1234567890BC}
AppName=Synora Studio Desktop
AppVersion=9.0.0
AppPublisher=Arean Narrayan
DefaultDirName={commonpf}\Synora Studio Desktop
DefaultGroupName=Synora Studio Desktop
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=Synora_Studio_Desktop_Setup_v9.0.0
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=..\resources\app_icon.ico
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\Synora_Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{commondesktop}\Synora Studio Desktop"; Filename: "{app}\Synora_Studio.exe"
Name: "{commonprograms}\Synora Studio Desktop"; Filename: "{app}\Synora_Studio.exe"
