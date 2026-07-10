# 河南方言语音板 🗣️

把「说家乡话」变成可听、可读、可学、可分享的**桌面软件**。

录一段河南话 → **方言转写** → **普通话对照 + 拼音 + 逐词拼音** → **释义** → **生成可分享方言卡片**。

**纯桌面应用（PySide6 原生 GUI）** —— 无浏览器、无 localhost，双击即真正的软件窗口。无任何密钥也能以「演示模式」跑通整条链路（内置 1106 条方言词库兜底）。

---

## ✨ 功能（v2.0）

- 🎙 **离线语音识别**：基于 FunASR Paraformer ONNX 量化模型，纯 CPU 推理（`onnxruntime`，**无需 PyTorch**），录音在本机完成识别，隐私零上传。
- 🔤 **方言解析**：输入或识别到的方言 → 普通话对照 + 拼音 + 逐词拼音 + 释义（大模型或内置词库）。
- 📚 **河南方言词库**：内置 **1106** 条河南方言词条（`dialect_dict.json` + `dialect_dict_extra.json` + `dialect_dict_m2.json`），`pypinyin` 注音，覆盖 18 地市说法差异。
- 🎮 **学习互动**：`page_game.py` 三模式——猜方言（4 选项 + 计分 + TTS 朗读，答错入错词本）、学习卡（大字 + 拼音 + 释义 + 翻页 + 朗读 + 洗牌）、错词本（复习 / 移除 / 清空）。
- ⚙️ **设置面板**：主题（暗 / 亮）、字号（标准 / 大 / 长辈）、识别引擎（自动 / 离线 / 讯飞 / FunASR）、TTS 音色、大模型 API（Key / Base URL / 模型名，写入本机 `.env`）、关闭最小化到托盘。
- 🌗 **亮色主题**：浅色配色与暗色一键切换、即时生效。
- 📌 **系统托盘**：关闭窗口最小化到托盘，双击恢复。
- 🃏 **方言卡片 / 📜 历史收藏 / 🗺 方言地图 / 🖼 方言画廊**：完整桌面体验。
- 🗄 **SQLite 数据层**：历史 / 收藏 / 错词本 / 设置存 `~/.henan_dialect/user_data.db`（WAL + 锁串行），首次启动自动迁移旧 JSON。

---

## 🧱 技术栈

| 用途 | 技术 |
|------|------|
| GUI | PySide6 (Qt6) |
| 离线识别 | `onnxruntime` + `kaldi_native_fbank` + FunASR Paraformer ONNX 量化模型 |
| 拼音 | `pypinyin` |
| 音频 | `sounddevice` / `soundfile` |
| 持久化 | Python `sqlite3` |
| 运行环境 | Python 3.13 |

---

## 📂 项目结构

```
河南方言语音板/
├── main.py                  # 桌面入口：QApplication + 主窗口 + 导航
├── store.py                 # 历史/收藏/错词本/设置 本地持久化（SQLite）
├── theme.py                 # 暗灰+翠绿情报终端 QSS 主题
├── worker.py                # 后台线程（避免 UI 卡顿）
├── recorder.py              # 麦克风录音 + 实时音量电平
├── utils.py                 # 通用工具
├── page_main.py / page_map.py / page_game.py / page_gallery.py / page_records.py
├── backend/                 # 后端逻辑包：词库/拼音/讯飞ASR/FunASR/大模型/纠错/demo
├── asr/                     # 识别引擎抽象：ASREngine 基类 + FunASR ONNX 实现
├── assets/
│   ├── asr_models/paraformer_zh/   # 离线识别模型（model.onnx 等，见下方说明）
│   └── illustrations/              # 方言插画
├── dialect_dict.json / dialect_dict_extra.json / dialect_dict_m2.json
├── installer/               # InnoSetup 安装包脚本（.iss）
├── tests/                   # 单元测试（unittest，零重型依赖）
├── docs/                    # 设计文档 / 发布说明
├── 河南方言语音板.spec      # PyInstaller 打包规格
├── make_dist.py             # 生成可分发的 zip 包
├── requirements.txt / requirements-test.txt / requirements-dev.txt
├── .env.example             # 密钥模板
└── .github/workflows/ci.yml # CI：push/PR 跑 compileall + 单测
```

> 旧版「Flask + 浏览器」网页实现已归档在 `网页版遗留/`，仅供回溯参考。

---

## 🚀 快速开始

### 方式一：发布版（推荐，无需 Python）

从 Releases 下载 `河南方言语音板_vYYYYMMDD.zip`，解压后双击 `河南方言语音板/河南方言语音板.exe` 即用。
开箱即「演示模式」（离线、不联网）。想用真实录音识别，按下方配置 `.env` + 装 FFmpeg。

### 方式二：源码运行

```bash
pip install -r requirements.txt
python main.py
```

> 录音需要本机麦克风；讯飞方言 ASR / 离线识别转码需要 FFmpeg：
> `winget install ffmpeg`（或 https://ffmpeg.org 下载后加入 PATH）。
> 没装也能跑演示模式；用真实录音识别请装 FFmpeg。

### （可选）配置密钥

不配置也能直接体验「演示模式」。要接真实识别 / 释义：

```bash
cp .env.example .env
# 编辑 .env，填入：
#   XF_APPID / XF_API_KEY / XF_API_SECRET   （讯飞开放平台 console.xfyun.cn）
#   LLM_API_KEY                              （DeepSeek / 通义千问等）
```

`.env` 放在 exe / 脚本同目录或工作目录均可被读取，**已加入 `.gitignore`，绝不入库**。

---

## 🧩 离线识别模型（不随仓库分发）

离线识别权重 `assets/asr_models/paraformer_zh/`（`model.onnx` 约 238MB + `am.mvn` + `tokens.json` + `tokens.txt`）**体积较大，不进 git**，请从以下任一方式获取后放入该目录：

1. **从发布包复制**：解压 `河南方言语音板_vYYYYMMDD.zip`，把其中的 `assets/asr_models/paraformer_zh/` 整目录复制到项目同名位置；
2. **从 ModelScope 下载** Paraformer-large ONNX 量化版，导出为 `model_quant.onnx` 并重命名为 `model.onnx`，连同 `am.mvn` / `tokens.txt` 放入。

缺少模型时，设置里的「离线识别」会提示需先部署模型；其余功能不受影响。

---

## 🧪 测试

```bash
pip install -r requirements-test.txt
python -m unittest discover -s tests
```

测试覆盖 `store`（SQLite 增删改查 / 去重 / 上限 / 旧 JSON 迁移）与 `backend`（纠错 / demo / 词库聚合），共 19 项，不依赖 PySide6 / onnxruntime / 网络。

---

## 📦 构建为 exe

```bash
# 用全新时间戳目录避免 Windows Defender 持锁导致清理失败
set HB_BUILD_DIR=河南方言语音板_b20260710_build
pyinstaller 河南方言语音板.spec
python make_dist.py        # 选中最新构建目录，生成发布 zip
```

产物为 `dist/<HB_BUILD_DIR>/河南方言语音板.exe`；`make_dist.py` 汇总为 `河南方言语音板_vYYYYMMDD.zip`。

安装包（`setup.exe`）由 `installer/河南方言语音板_installer.iss` 经 InnoSetup 编译生成（需本机安装 InnoSetup）。

---

## 🛡️ 安全红线

- **绝不**把 APPID / APIKey / APISecret 写进前端或提交到公开仓库。
- Key 一律从 `.env` 读取，`.env` 已在 `.gitignore` 忽略。
- 历史 / 收藏 / 错词本仅存本机用户目录（`~/.henan_dialect`），不上传任何服务器。

---

## 📄 许可证

详见 [`docs/LICENSE`](docs/LICENSE)。

---

