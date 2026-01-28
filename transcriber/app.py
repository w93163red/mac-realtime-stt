"""应用主模块"""

import threading

from .config import (
    AppConfig,
    AudioConfig,
    DisplayConfig,
    ProcessingConfig,
    TranscriptionConfig,
    TranslationConfig,
)
from .display_gui import SubtitleDisplayCoordinator
from .processor_realtimestt import RealtimeSTTProcessor
from .translation import Translator


class TranscriberApp:
    """实时字幕翻译应用（GUI 模式）"""

    def __init__(
        self,
        audio_config: AudioConfig = None,
        transcription_config: TranscriptionConfig = None,
        translation_config: TranslationConfig = None,
        processing_config: ProcessingConfig = None,
        display_config: DisplayConfig = None,
        app_config: AppConfig = None,
    ):
        # 如果提供了 AppConfig，优先使用它
        if app_config:
            self.app_config = app_config
            self.audio_config = app_config.audio
            self.transcription_config = app_config.transcription
            self.translation_config = app_config.translation
            self.processing_config = app_config.processing
            self.display_config = app_config.display
        else:
            # 兼容旧的初始化方式
            self.app_config = None
            self.audio_config = audio_config
            self.transcription_config = transcription_config
            self.translation_config = translation_config
            self.processing_config = processing_config
            self.display_config = display_config

        # 初始化双窗口显示协调器（传递 config）
        self.display = SubtitleDisplayCoordinator(
            max_visible_items=self.display_config.max_visible_items,
            context_size=self.display_config.translation_context_size,
            config=self.app_config,
        )

        # 初始化其他组件
        self.translator = Translator(self.translation_config)
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
            audio_device_name=self.audio_config.device_name,
        )

        # 启动处理线程
        self._process_thread = threading.Thread(
            target=self.processor.run, daemon=True
        )
        self._process_thread.start()

        self.display.print("🟢 开始监听...")

    def run(self):
        """运行应用（GUI 模式）"""
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

    def stop(self):
        """停止应用"""
        if self.processor:
            self.processor.stop()
        if hasattr(self.display, "quit"):
            self.display.quit()
