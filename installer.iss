; Optional installer. Build dist\TimeCalculator.exe first (build.bat), then open this in Inno Setup 6 and press Compile.
[Setup]
AppName=Time Calculator
AppVersion=1.0.0
DefaultDirName={autopf}\Time Calculator
DefaultGroupName=Time Calculator
OutputBaseFilename=TimeCalculator-Setup
OutputDir=dist
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\TimeCalculator.exe

[Files]
Source: "dist\TimeCalculator.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Time Calculator"; Filename: "{app}\TimeCalculator.exe"
Name: "{autodesktop}\Time Calculator"; Filename: "{app}\TimeCalculator.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\TimeCalculator.exe"; Description: "Launch Time Calculator"; Flags: nowait postinstall skipifsilent
