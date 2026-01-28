"""应用主模块"""

import threading
from typing import Literal

import sounddevice as sd
from rich.live import Live

from .config import (
    AudioConfig,
    DisplayConfig,
    ProcessingConfig,
    TranscriptionConfig,
    TranslationConfig,
)
from .display_gui import SubtitleGUIDisplay
from .processor_realtimestt import RealtimeSTTProcessor
from .translation import Translator


class TranscriberApp:
    """实时字幕翻译应用"""

    def __init__(
        self,
        audio_config: AudioConfig,
        transcription_config: TranscriptionConfig,
        translation_config: TranslationConfig,
        processing_config: ProcessingConfig,
        display_config: DisplayConfig,
        ui_mode: Literal["tui", "gui"] = "gui",
    ):
        self.audio_config = audio_config
        self.transcription_config = transcription_config
        self.translation_config = translation_config
        self.processing_config = processing_config
        self.display_config = display_config
        self.ui_mode = ui_mode

        # 根据模式初始化显示组件
        if ui_mode == "gui":
            self.display = SubtitleGUIDisplay(
                max_visible_items=display_config.max_visible_items,
                context_size=display_config.translation_context_size,
            )
        else:
            self.display = SubtitleDisplay()

        # 初始化其他组件
        self.translator = Translator(translation_config)
        self.processor = None  # 延迟初始化

        self._process_thread = None
        self._init_thread = None

    def _initialize_components(self):
        """初始化组件（在后台线程中）"""
        self.display.print("加载 Whisper 模型和 VAD...")

        self.display.print(
            f"源语言: {self.transcription_config.source_lang} | "
            f"目标语言: {self.translation_config.target_lang}"
        )

        # 创建 RealtimeSTT 处理器
        self.processor = RealtimeSTTProcessor(
            translator=self.translator,
            display=self.display,
            model=self.transcription_config.model_name,
            language=self.transcription_config.source_lang,
            device=self.transcription_config.device,
            compute_type=self.transcription_config.compute_type,
            translation_delay=self.processing_config.translation_delay,
            audio_device_name=self.audio_config.device_name,
        )

        # 启动处理线程
        self._process_thread = threading.Thread(
            target=self.processor.run, daemon=True
        )
        self._process_thread.start()

        self.display.print("🟢 开始监听...")

    def run(self):
        """运行应用"""
        if self.ui_mode == "gui":
            self._run_gui()
        else:
            self._run_tui()

    def _run_gui(self):
        """运行 GUI 模式"""
        # 在后台线程初始化组件
        self._init_thread = threading.Thread(
            target=self._initialize_components, daemon=True
        )
        self._init_thread.start()

        # 在主线程运行 GUI
        try:
            self.display.run()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def _run_tui(self):
        """运行 TUI 模式"""
        self._initialize_components()

        # 开始录音并使用 Rich Live 显示
        try:
            with Live(
                self.display.get_panel(),
                refresh_per_second=self.display_config.refresh_per_second,
                console=self.display.console,
            ) as live:
                while True:
                    live.update(self.display.get_panel())
                    sd.sleep(self.display_config.update_interval_ms)
        except KeyboardInterrupt:
            self.display.print("\n停止监听")
        finally:
            self.stop()

    def stop(self):
        """停止应用"""
        if self.processor:
            self.processor.stop()
        if self.ui_mode == "gui" and hasattr(self.display, "quit"):
            self.display.quit()
