; 河南方言语音板 · InnoSetup 安装向导脚本
; 用法（在用户本机）：
;   1) 安装 InnoSetup（https://jrsoftware.org/isdl.php）
;   2) 已用 build_exe.bat 生成 dist\河南方言语音板.exe
;   3) 用 InnoSetup 打开本文件并编译，得到 installer\河南方言语音板_setup.exe
; 编译前请确保 dist\河南方言语音板.exe 与下列文件与本 .iss 同级存在。

[Setup]
AppName=河南方言语音板
AppVersion=1.0
AppPublisher=hua
DefaultDirName={pf}\河南方言语音板
DefaultGroupName=河南方言语音板
OutputDir=installer
OutputBaseFilename=河南方言语音板_setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\河南方言语音板.exe

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\河南方言语音板.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: ".env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "河南方言语音板_发布说明.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\河南方言语音板"; Filename: "{app}\河南方言语音板.exe"
Name: "{commondesktop}\河南方言语音板"; Filename: "{app}\河南方言语音板.exe"
Name: "{group}\卸载 河南方言语音板"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\河南方言语音板.exe"; Description: "立即启动 河南方言语音板"; Flags: nowait postinstall skipifsilent
