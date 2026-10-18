#ifndef BuildId
  #define BuildId "dev"
#endif
[Setup]
AppId={{35089A9A-26B0-485E-B3BB-3FF5E0F41FB5}
AppName=Matrix Desktop Preview
AppVersion=0.1.0
AppPublisher=Matrix contributors
DefaultDirName={localappdata}\Programs\MatrixPreview
DefaultGroupName=Matrix Desktop Preview
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist\windows
OutputBaseFilename=MatrixPreview-0.1.0-{#BuildId}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\MatrixPreview.exe
InfoBeforeFile=preview-notice.txt

[Files]
Source: "..\..\dist\MatrixPreview\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Matrix Desktop Preview"; Filename: "{app}\MatrixPreview.exe"
Name: "{group}\Uninstall Matrix Desktop Preview"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\MatrixPreview.exe"; Description: "Launch Matrix Desktop Preview"; Flags: nowait postinstall skipifsilent
