# 🎙 AI Voice Assistant

一个**个人语音助手**：对着电脑说话，它就能听懂、思考并用**自然的人声**回答你。

- 语音识别：豆包大模型 ASR（火山引擎）
- 对话大脑：DeepSeek（支持函数调用工具）
- 语音合成：豆包 Seed TTS 2.0（自然音色，非机器音）
- 界面：现代深色主题，带波形动画

## ✨ 功能

- **持续语音对话**：自动检测你说话（说完自动回复），也可切换「按住说话」模式
- **打断**：它说话时你直接开口，就能打断它
- **自然音色**：豆包语音合成，多种男声/女声可选
- **对话记忆**：跨会话记住聊过的内容
- **实用工具**：查时间/日期、计算器（可扩展）
- **现代界面**：波形动画状态指示、空格键说话、清空对话/清除记忆按钮

## 🏗 架构

```
麦克风 → 豆包 ASR（识别）→ DeepSeek（对话+工具）→ 豆包 TTS（合成）→ 扬声器播放
```

所有核心逻辑都封装成独立模块，方便替换或复用。

## 📋 环境要求

- Windows（本机开发环境）
- Python 3.12（推荐，3.13 亦可）

## 🚀 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv .venv

# 激活（Windows）
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 API 密钥

复制配置模板，填入你自己的密钥：

```bash
cp config.example.json config.json
```

编辑 `config.json`，填入：

| 字段 | 说明 | 获取方式 |
|------|------|---------|
| `llm.api_key` | DeepSeek API Key | [platform.deepseek.com](https://platform.deepseek.com) |
| `stt.api_key` | 火山引擎语音 API Key（**UUID 格式**） | [console.volcengine.com/speech](https://console.volcengine.com/speech) →「API Key 管理」 |
| `tts.api_key` | 同上 | 同上 |

> ⚠️ 注意：语音识别/合成用的是**火山引擎语音控制台里的 UUID 格式 API Key**，不是方舟（Ark）的 `ark-` 开头 key。

### 3. 运行

```bash
python main.py
```

启动后等几秒加载，窗口状态变成「聆听中」就能说话了。

## 🎤 使用说明

- **自动检测模式**（默认）：直接说话，说完停顿约 0.5 秒，自动回复
- **按键说话模式**：切换模式后，**按住「按住说话」按钮或空格键**说话，松开回复
- **打断**：助手说话时直接开口，它就会停下听你说
- **清空对话**：清掉界面日志
- **清除记忆**：清掉对话历史（删 `memory.json`）

## 🎨 自定义

所有可定制项都在 `config.json`：

- `assistant.name`：助手名字
- `assistant.personality`：人设/性格
- `assistant.wake_word`：唤醒词（预留）
- `tts.voice`：音色（如 `zh_female_tianmeitaozi_uranus_bigtts` 甜美女声、`zh_male_jieshuoxiaoming_uranus_bigtts` 男声）
- `vad.energy_threshold`：麦克风灵敏度（识别不到就调小，太灵敏就调大）
- `mode`：默认模式（`auto` / `push`）

## 📁 项目结构

```
├── main.py            # 入口 + 现代深色 GUI
├── audio.py           # 麦克风采集
├── vad.py             # 语音活动检测（判断开始/结束说话）
├── stt.py             # 豆包语音识别（ASR）
├── llm.py             # DeepSeek 对话 + 函数调用工具
├── tools.py           # 工具层（查时间、计算器）
├── tts.py             # 豆包语音合成（TTS）
├── conversation.py    # 对话状态机（自动/按键 + 打断）
├── config.example.json # 配置模板（不含真实密钥）
├── config.json        # 你的配置（含密钥，已 gitignore）
└── requirements.txt   # 依赖清单
```

## 🔧 扩展

- **加工具**：在 `tools.py` 里加一个函数 + 一条 `TOOLS` 定义，DeepSeek 就会自动学会调用
- **换对话模型**：改 `config.json` 的 `llm.base_url` / `llm.model`，可换成任意 OpenAI 兼容接口

## 📝 隐私说明

- `config.json`（含 API 密钥）和 `memory.json`（对话记忆）已加入 `.gitignore`，不会上传
- 对话记忆保存在本地 `memory.json`，可随时点「清除记忆」删除
