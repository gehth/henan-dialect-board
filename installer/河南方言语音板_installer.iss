; =====================================================================
; 河南方言语音板 · InnoSetup 安装脚本 (v2.0.0)
; ---------------------------------------------------------------------
; 编译方法（任选其一）：
;   1) 用 InnoSetup 6 打开本文件，按 F9 编译；
;   2) 命令行（推荐，自动定位最新构建目录）：
;      build_installer.bat
;   或手动指定源目录：
;      "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" ^
;        /DMySourceDir="dist/河南方言语音板_b20260710_slim" ^
;        installer/河南方言语音板_installer.iss
;
; 源目录：dist/河南方言语音板_b*（已用 PyInstaller 打好的 onedir 文件夹，
;          由 build_installer.bat 自动挑选最新一份并通过 /DMySourceDir 传入）
; 安装后：开始菜单 + 可选桌面快捷方式，并自带标准卸载程序。
; 注：本程序无需管理员权限，默认安装到当前用户的 Programs 目录。
; =====================================================================

#define MyAppName      "河南方言语音板"
#define MyAppVersion   "2.0.0"
#define MyAppPublisher "河南方言语音板"
#define MyAppURL       "https://github.com/gehth/henan-dialect-board"

; 源目录：命令行 /DMySourceDir 可覆盖；缺省指向最近一次瘦身构建。
#ifndef MySourceDir
#define MySourceDir "dist/河南方言语音板_b20260710_slim"
#endif

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
ArchitecturesInstallIn64BitMode=x64os
ArchitecturesAllowed=x64os

; 输出到项目根 dist\（本脚本位于 installer\，故用 ..\dist 回到项目根）
OutputDir=..\dist
OutputBaseFilename=河南方言语音板_setup
; 压缩：lzma2/max 在体积与编译耗时间取得较好平衡（约 500MB）
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; 普通用户即可安装，不弹 UAC
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
; 卸载时若程序在运行，提示关闭
CloseApplications=yes
UninstallDisplayIcon={app}\河南方言语音板.exe
SetupLogging=yes
UsedUserAreasWarning=no

[Languages]
; 本机 InnoSetup 默认语言包未含中文，故以内置 Default.isl 为基，
; 再用下方 [Messages] 段把向导关键文案覆写为中文，无需额外下载语言文件。
Name: "chinese"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel1=欢迎使用 {#MyAppName} 安装向导
WelcomeLabel2=本向导将引导您完成 {#MyAppName} 的安装。
ClickNext=点击“下一步”继续。
SelectDirLabel3=将 {#MyAppName} 安装到以下文件夹：
SelectDirBrowseLabel=如要安装到其他文件夹，点击“浏览”。
ReadyLabel1=准备安装 {#MyAppName}
InstallingLabel=正在安装 {#MyAppName}，请稍候…
FinishedHeadingLabel=完成 {#MyAppName} 安装向导
FinishedLabelNoIcons={#MyAppName} 已成功安装到您的计算机。
FinishedLabel={#MyAppName} 已成功安装到您的计算机。
ClickFinish=点击“完成”退出安装向导。
ButtonNext=下一步(&N)
ButtonBack=上一步(&B)
ButtonCancel=取消
ButtonInstall=安装(&I)
ButtonFinish=完成(&F)
ExitSetupMessage=若要退出安装向导，请点击“取消”。
ExitSetupTitle=退出安装向导
DiskSpaceMBLabel=所需磁盘空间：约 %1 MB
DirExistsTitle=文件夹已存在
DirExists=指定的文件夹已存在。是否继续？
NoUninstallWarningTitle=无法卸载
NoUninstallWarning=无法找到先前的版本，是否继续安装？

[Files]
; 把整个 onedir 文件夹原样拷贝到安装目录
Source: "{#MySourceDir}/*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

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
