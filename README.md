# Mac 实时字幕 + 翻译

使用 BlackHole + faster-whisper + DeepSeek 实现的实时字幕和翻译工具。

## 特性

- 🎤 实时音频捕获
- 📝 离线语音识别（faster-whisper）
- 🌍 实时翻译（DeepSeek API）
- 🖥️ GUI 界面（Tkinter）- 滚动字幕历史
- 💬 每句话独立显示，翻译异步追加
- ⚡ 滑动窗口 + VAD 智能分段，低延迟

## 安装

1. 安装 BlackHole 虚拟音频设备：
```bash
brew install blackhole-2ch
```

2. 在 Audio MIDI Setup 中创建 Multi-Output Device

3. 安装 Python 依赖：
```bash
uv pip install -r requirements.txt
```

## 使用

**GUI 模式（默认，推荐）：**
```bash
python run.py
```

**TUI 模式：**
```bash
python run.py --tui
```

## 界面说明

### GUI 模式
- 类似聊天窗口的滚动界面
- 每个句子独立显示为一个卡片
- 原文立即显示（蓝色 🎤）
- 翻译异步追加（绿色 🌍）
- 支持鼠标滚轮查看历史记录

### TUI 模式
- 终端内实时更新的字幕面板
- 原文和翻译在同一位置刷新显示

## 项目结构

```
transcriber/
├── __init__.py          # 包初始化
├── config.py            # 配置定义（dataclass）
├── audio.py             # 音频捕获（AudioCapture）
├── transcription.py     # 语音转录（Transcriber）
├── translation.py       # 文本翻译（Translator）
├── display.py           # TUI 显示（SubtitleDisplay）
├── display_gui.py       # GUI 显示（SubtitleGUIDisplay）
├── processor.py         # 音频处理器（AudioProcessor）
└── app.py              # 应用主类（TranscriberApp）

run.py                   # 入口文件
```

## 配置

在 `transcriber/config.py` 中可以修改：

- 音频参数（采样率、设备名称等）
- Whisper 模型（tiny/base/small/medium/large）
- 翻译 API 设置
- 处理参数（窗口大小、处理间隔等）
- 显示刷新率

## 架构设计

遵循单一职责原则，每个模块负责特定功能：

- **AudioCapture**: 音频设备管理和数据捕获
- **Transcriber**: Whisper 模型封装，负责语音转文字
- **Translator**: 翻译 API 封装
- **SubtitleDisplay**: Rich TUI 显示管理（覆盖更新）
- **SubtitleGUIDisplay**: Tkinter GUI 显示管理（滚动历史）
- **AudioProcessor**: 协调音频处理流程（滑动窗口、VAD、异步翻译、句子分割）
- **TranscriberApp**: 应用生命周期管理，支持 GUI/TUI 切换

### 句子分割逻辑

- 检测句子结束标点（`.` `!` `?` `。` `！` `？`）
- 完整句子立即输出为新条目
- 未完成句子只在显著变化时更新
- 避免重复输出相同内容

## License

MIT
