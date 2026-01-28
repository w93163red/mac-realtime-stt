#!/usr/bin/env python3
"""
Mac 实时字幕 + 翻译
BlackHole + RealtimeSTT + DeepSeek

使用前：
1. 安装 BlackHole: brew install blackhole-2ch
2. 系统设置 -> 声音 -> 输出 -> 选择 "Multi-Output Device"（需要先在 Audio MIDI Setup 中创建）
3. 设置环境变量: export DEEPSEEK_API=your_key

使用方法：
  python run.py
"""

from transcriber.app import TranscriberApp
from transcriber.config import (
    AudioConfig,
    DisplayConfig,
    ProcessingConfig,
    TranscriptionConfig,
    TranslationConfig,
)


def main():
    """主函数"""
    # 创建配置
    audio_config = AudioConfig()
    transcription_config = TranscriptionConfig()
    translation_config = TranslationConfig()
    processing_config = ProcessingConfig()
    display_config = DisplayConfig()

    # 创建并运行应用（GUI 模式）
    app = TranscriberApp(
        audio_config=audio_config,
        transcription_config=transcription_config,
        translation_config=translation_config,
        processing_config=processing_config,
        display_config=display_config,
    )

    app.run()


if __name__ == "__main__":
    main()
