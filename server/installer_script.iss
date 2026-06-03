[Setup]
AppId={{3B4C5D6E-F7A8-9012-BCDE-234567890CDE}
AppName=Synora Studio Server
AppVersion=9.0.0
AppPublisher=Arean Narrayan
DefaultDirName={commonpf}\Synora Studio Server
DefaultGroupName=Synora Studio Server
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=Synora_Studio_Server_Setup_v9.0.0
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=..\resources\app_icon.ico
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\server\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{commonprograms}\Synora Studio Server"; Filename: "{app}\API_Server.exe"
