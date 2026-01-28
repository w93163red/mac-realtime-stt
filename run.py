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
from transcriber.config import AppConfig


def main():
    """主函数"""
    # 创建统一配置（自动加载 JSON 配置和环境变量）
    config = AppConfig()

    # 创建并运行应用（GUI 模式）
    app = TranscriberApp(app_config=config)

    app.run()


if __name__ == "__main__":
    main()
