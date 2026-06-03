[Setup]
AppId={{5D6E7F8A-B901-2345-CDEF-4567890DEF12}
AppName=Synora Admin Reset Tool
AppVersion=9.0.0
AppPublisher=Arean Narrayan
DefaultDirName={commonpf}\Synora Admin Reset Tool
DefaultGroupName=Synora Admin Reset Tool
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=Synora_Admin_Reset_Setup_v9.0.0
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=..\..\resources\app_icon.ico
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\operator_tools\Admin_Reset"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{commonprograms}\Synora Admin Reset Tool"; Filename: "{app}\Admin_Reset.exe"
