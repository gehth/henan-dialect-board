; =====================================================================
; 河南方言语音板 · InnoSetup 安装脚本
; ---------------------------------------------------------------------
; 编译方法（任选其一）：
;   1) 用 InnoSetup 6 打开本文件，按 F9 编译；
;   2) 命令行直接编译：
;      "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" 河南方言语音板_installer.iss
; 编译产物：dist\河南方言语音板_setup.exe（单文件安装包）
;
; 源目录：dist\河南方言语音板_build\（已用 PyInstaller 打好的 onedir 文件夹）
; 安装后：开始菜单 + 可选桌面快捷方式，并自带标准卸载程序。
; 注：本程序无需管理员权限，默认安装到当前用户的 Programs 目录。
; =====================================================================

#define MyAppName      "河南方言语音板"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "河南方言语音板"
#define MyAppURL       "https://github.com/"
#define MySourceDir    "dist\河南方言语音板_build"

[Setup]
; 固定 AppId，保证升级/卸载时能正确识别同一应用
AppId={{A1B2C3D4-1234-5678-9ABC-DEF012345678}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
VersionInfoVersion={#MyAppVersion}
VersionInfoDescription={#MyAppName} 安装程序
VersionInfoCopyright=Copyright (C) 2026 {#MyAppPublisher}

; 安装位置：当前用户 Programs 目录，无需管理员权限
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; 64 位 Only（Qt6/PySide6 仅 64 位）
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64

OutputDir=dist
OutputBaseFilename=河南方言语音板_setup
; 压缩：lzma2/max 在体积与编译耗时间取得较好平衡（约 250~280MB）
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; 普通用户即可安装，不弹 UAC
PrivilegesRequired=lowest
; 卸载时若程序在运行，提示关闭
CloseApplications=yes
UninstallDisplayIcon={app}\河南方言语音板.exe
SetupLogging=yes

[Languages]
Name: "chinese"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Files]
; 把整个 onedir 文件夹原样拷贝到安装目录
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\河南方言语音板.exe"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\河南方言语音板.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "额外快捷方式："; Flags: unchecked

[Run]
; 安装结束可选「立即运行」
Filename: "{app}\河南方言语音板.exe"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall runascurrentuser

[UninstallDelete]
; 清理可能残留的用户配置（可选；TTS 缓存位于用户目录，不在此清理）
Type: filesandordirs; Name: "{localappdata}\Programs\{#MyAppName}"
