# 河南方言语音板 🗣️

把「说家乡话」变成可听、可读、可学、可分享的**桌面软件**。

录一段河南话 → **方言转写** → **普通话对照 + 拼音 + 逐词拼音** → **释义** → **生成可分享方言卡片**。

**纯桌面应用（PySide6 原生 GUI）** —— 不再有浏览器、不再有 localhost，双击就是一个真正的软件窗口。无任何密钥也能以「演示模式」跑通整条链路（内置方言词库兜底）。

---

## ✨ 功能

- 🎙 **录音识别**：调用麦克风录音（sounddevice），自动转 16k/单声道，送讯飞方言 ASR 识别；无麦克风或没配密钥时自动降级演示
- 🔤 **方言解析**：输入或识别到的方言 → 普通话对照 + 拼音 + 逐词拼音 + 释义（大模型或内置词库）
- 🃏 **方言卡片**：一键生成可保存的方言卡片（PNG）
- 📜 **历史与收藏**：每次解析自动记历史，可手动收藏，存本机（不上传）
- 🗺 **方言地图**：河南轮廓 + 18 地市点位，点击看各地说法差异
- 🎮 **猜方言小游戏**：看方言选意思，计分 / 连击，支持朗读
- 🖼 **方言画廊**：AI 生成的河南乡土插画 + 词条释义
- 🔊 **朗读**：用系统语音引擎朗读方言 / 普通话

## 🧱 项目结构

```
河南方言语音板/
├── main.py              # 桌面入口：QApplication + 主窗口 + 导航 + 页面栈
├── backend.py           # 后端逻辑：词库/拼音/讯飞ASR/FunASR/大模型（去 Flask）
├── recorder.py          # 麦克风录音 + 实时音量电平
├── store.py             # 历史/收藏/错词本/设置 本地持久化（SQLite）
├── theme.py             # 暗灰+翠绿情报终端 QSS 主题
├── worker.py            # 后台线程（避免 UI 卡顿）
├── page_main.py         # 语音板页（解析/录音/收藏/卡片/朗读）
├── page_map.py          # 方言地图页
├── page_game.py         # 猜方言游戏页
├── page_gallery.py      # 方言画廊页
├── page_records.py      # 我的记录页（历史/收藏）
├── dialect_dict.json    # 内置河南方言词库 + 18 地市差异（演示 & LLM 兜底）
├── assets/illustrations/# AI 生成的方言插画（nongshale/deijin/zhongbuzhong/huimian）
├── requirements.txt     # 运行依赖
├── 河南方言语音板.spec   # PyInstaller 打包配置（裁剪+锁规避）
├── build_installer.bat  # 一键生成安装包 setup.exe（需本机装 InnoSetup）
├── .env.example         # 密钥模板
├── dist/河南方言语音板.exe   # 打包好的发布版（双击即用）
└── README.md
```

> 旧版「Flask + 浏览器」网页实现已归档在 `网页版遗留/` 子目录，仅供回溯参考，不参与桌面版运行。

## 🚀 快速开始

### 方式一：直接用发布版（推荐，无需 Python）

把 `dist/河南方言语音板.exe` 这一个文件发给同学 / 老师，**双击即用**，自动弹出软件窗口。
开箱即「演示模式」（离线、不联网）。想用真实语音识别，按下方配置 `.env` + 装 FFmpeg。

### 方式二：源码运行

```bash
pip install -r requirements.txt
python main.py
```

> 录音需要本机有可用麦克风；讯飞方言 ASR 需要 FFmpeg（把录音转 16k 单声道）：
> `winget install ffmpeg`（或官网 https://ffmpeg.org 下载后加入 PATH）。
> 没装也能跑演示模式；要用真实录音识别请装 FFmpeg。

### （可选）配置密钥

不配置也能直接体验「演示模式」。要接真实识别 / 释义：

```bash
cp .env.example .env
# 编辑 .env，填入：
#   XF_APPID / XF_API_KEY / XF_API_SECRET   （讯飞开放平台 console.xfyun.cn）
#   LLM_API_KEY                              （DeepSeek platform.deepseek.com 或 通义千问）
```

`.env` 放在 exe / 脚本同目录或工作目录均可被读取。

## 🔌 运行模式

| 模式 | 条件 | 说明 |
|------|------|------|
| 演示模式 | 无任何密钥 | 内置 75 条词库兜底，解析 / 拼音 / 释义全可用，录音识别降级提示 |
| 云端模式 | 配置讯飞 + 大模型 | 真实方言 ASR 转写 + 大模型释义 |
| 离线识别 | 安装 funasr + ffmpeg | 录音本机识别，隐私零上传 |

主窗口状态栏会实时显示当前模式（演示 / 云端 / 离线）。

## 🛡️ 安全红线

- **绝不**把 APPID / APIKey / APISecret 写进前端或提交到公开仓库。
- Key 一律从 `.env` 读取，`.env` 已在 `.gitignore` 忽略。
- 历史 / 收藏仅存本机用户目录（`~/.henan_dialect`），不上传任何服务器。

## 🧩 本地离线识别（FunASR，隐私零上传）

不依赖任何云端密钥，录音在**本机**完成识别，适合隐私敏感场景或毕业设计演示：

```bash
pip install funasr
winget install ffmpeg          # 离线识别同样需要 ffmpeg 做 16k 转码
python main.py
```

> **排错**：若 `pip install funasr` 报 `Failed building wheel for editdistance`（该包需要从源码编译 C 扩展，要求本机有 C 编译环境），改用预编译轮子即可：
> ```bash
> pip install editdistance --only-binary :all:
> pip install funasr
> ```
> 或用 conda：`conda install -c conda-forge funasr`。
> 注：当前开发沙箱缺编译工具链，已实测无法安装 funasr（editdistance 编译失败）；离线识别请在**本地机器**运行，代码与开关已就绪、装好即自动启用。
> 首次识别会从 ModelScope 自动下载 `paraformer-large`（+ VAD + 标点）模型，约数百 MB，请确保磁盘与网络充足；下载后可离线复用。可用环境变量 `OFFLINE_ASR_MODEL` 指定自定义 / 微调模型。

## 📦 打包为 exe

```bash
# 方式一：基于 spec 打包（推荐，已内置裁剪与 Defender 锁规避）
set HB_BUILD_DIR=河南方言语音板_b<YYYYMMDD_HHMMSS>
pyinstaller 河南方言语音板.spec

# 方式二：一键生成安装包（setup.exe，需本机装 InnoSetup）
build_installer.bat
```

产物在 `dist/河南方言语音板.exe`。

---

由 WorkBuddy 生成 · 暗灰/翠绿情报终端风格
