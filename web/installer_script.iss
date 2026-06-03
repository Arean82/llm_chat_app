[Setup]
AppId={{4C5D6E7F-A8B9-0123-CDEF-34567890DEF1}
AppName=Synora Studio Web Portal
AppVersion=9.0.0
AppPublisher=Arean Narrayan
DefaultDirName={commonpf}\Synora Studio Web Portal
DefaultGroupName=Synora Studio Web Portal
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=Synora_Studio_Web_Portal_Setup_v9.0.0
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=..\resources\app_icon.ico
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\web\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{commonprograms}\Synora Studio Web Portal"; Filename: "{app}\SaaS_Web_Portal.exe"
