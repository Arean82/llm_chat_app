[Setup]
AppId={{6E7F8A9B-0123-4567-8901-CDEF23456789}
AppName=Synora Companion Operation
AppVersion=9.0.0
AppPublisher=Arean Narrayan
DefaultDirName={commonpf}\Synora Companion Operation
DefaultGroupName=Synora Companion Operation
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=Synora_Companion_Operation_Setup_v9.0.0
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=..\..\resources\app_icon.ico
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\operator_tools\Companion_Operation"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{commonprograms}\Synora Companion Operation"; Filename: "{app}\Companion_Operation.exe"
