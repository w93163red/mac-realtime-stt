# Mac 实时字幕 + 翻译

使用 BlackHole + RealtimeSTT + DeepSeek 实现的实时字幕和翻译工具。

## 特性

- 🎤 实时音频捕获（BlackHole 虚拟音频设备）
- 📝 离线语音识别（RealtimeSTT + faster-whisper）
- 🔊 双层 VAD 语音检测（WebRTCVAD + SileroVAD）
- 🌍 段落式实时翻译（DeepSeek API）
- 🖥️ GUI 界面（Tkinter）- 段落模式显示
- 💬 智能句子管理（最多保留6句话）
- ⚡ 低延迟实时转录和翻译

## 安装

1. 安装 BlackHole 虚拟音频设备：
```bash
brew install blackhole-2ch
```

2. 在 Audio MIDI Setup 中创建 Multi-Output Device，包含：
   - 内置扬声器（用于播放）
   - BlackHole 2ch（用于捕获系统音频）

3. 设置环境变量：
```bash
export DEEPSEEK_API="your-deepseek-api-key"
```

4. 安装 Python 依赖：
```bash
uv pip install -r requirements.txt
```

## 使用

```bash
python run.py
```

## 界面说明

**段落式 GUI 显示**：
- **段落式显示**：所有句子合并成一个连续段落
- **智能句子管理**：最多显示6句已完成的句子 + 1句正在说的句子
- **原文区域**（蓝色 🎤）：显示所有句子组成的段落
- **翻译区域**（绿色 🌍）：显示整个段落的翻译
- **自动滚动**：新内容自动滚动到可见区域
- **支持鼠标滚轮**：可以回看历史内容

显示格式：
```
🎤 句子1 句子2 句子3 句子4 句子5 句子6 当前正在说的句子...

🌍 完整的段落翻译内容...
```

## 项目结构

```
transcriber/
├── __init__.py              # 包初始化
├── config.py                # 配置定义（dataclass）
├── translation.py           # 文本翻译（Translator）
├── display_gui.py           # GUI 显示（SubtitleGUIDisplay）
├── processor_realtimestt.py # RealtimeSTT 处理器
└── app.py                   # 应用主类（TranscriberApp）

run.py                       # 入口文件
```

## 配置

### 环境变量
```bash
export DEEPSEEK_API="your-deepseek-api-key"
```

### 配置文件

在 [transcriber/config.py](transcriber/config.py) 中可以修改：

- **AudioConfig**: 音频设备名称（默认：BlackHole 2ch）
- **TranscriptionConfig**: Whisper 模型（tiny/base/small/medium/large）、设备（cpu/cuda）、计算类型
- **TranslationConfig**: DeepSeek API 设置、源语言、目标语言、温度、最大令牌数
- **ProcessingConfig**: 翻译延迟（未完成句子的翻译延迟，默认 0.5 秒）
- **DisplayConfig**: 显示刷新率、最大可见句子数（默认 6）、翻译上下文大小

## 架构设计

遵循单一职责原则，每个模块负责特定功能：

- **RealtimeSTTProcessor**: 基于 RealtimeSTT 的音频处理器
  - 集成 AudioToTextRecorder（音频捕获 + VAD + 转录）
  - 双层 VAD：WebRTCVAD（快速粗筛） + SileroVAD（精确检测）
  - 实时转录回调（未完成句子）+ 完整句子返回
  - 句子分割逻辑（按标点符号分割）
  - 异步翻译队列管理

- **Translator**: 翻译 API 封装
  - DeepSeek API 调用
  - 支持上下文传递（段落模式不使用）

- **SubtitleGUIDisplay**: Tkinter GUI 显示管理（段落模式）
  - 维护句子列表（最多 6 句）
  - 段落式显示（所有句子合并）
  - 整段翻译显示
  - 自动移除最旧句子

- **TranscriberApp**: 应用生命周期管理（GUI 模式）

### RealtimeSTT 特性

- **VAD 配置**：
  - `silero_sensitivity`: 0.3（VAD 灵敏度，0-1）
  - `webrtc_sensitivity`: 3（WebRTC VAD 灵敏度，0-3）
  - `post_speech_silence_duration`: 0.4 秒（句子结束后的静音时长）
  - `min_length_of_recording`: 0.5 秒（最小录音长度）

- **实时转录**：
  - `enable_realtime_transcription`: True（启用实时转录）
  - `realtime_processing_pause`: 0.1 秒（实时处理间隔）
  - `on_realtime_transcription_update`: 实时更新回调（未完成句子）

- **句子检测**：
  - `recorder.text()`: 阻塞等待完整句子
  - 自动句子分割：按 `.!?` 分割，处理缩写词

### 句子管理逻辑

1. **实时更新**（未完成句子）：
   - 通过 `on_realtime_transcription_update` 回调接收
   - 更新 GUI 的 `current_sentence`
   - 延迟翻译（0.5 秒后触发）

2. **完成句子**：
   - 通过 `recorder.text()` 返回
   - 按标点符号分割成多个句子
   - 批量添加到句子列表
   - 如果超过 6 句，移除最旧的句子
   - 立即翻译整个段落

3. **段落翻译**：
   - 获取所有句子（包括未完成的）
   - 合并成段落
   - 翻译整个段落（不需要上下文）
   - 更新 GUI 的 `paragraph_translation`

## License

MIT
