"""音频处理器模块"""

import queue
import threading
from typing import Optional

import numpy as np

from .audio import AudioCapture
from .config import AudioConfig, ProcessingConfig
from .transcription import Transcriber
from .translation import Translator


class AudioProcessor:
    """音频处理器"""

    def __init__(
        self,
        audio_capture: AudioCapture,
        transcriber: Transcriber,
        translator: Translator,
        display,
        config: ProcessingConfig,
        translation_delay: float = 2.0,
    ):
        self.audio_capture = audio_capture
        self.transcriber = transcriber
        self.translator = translator
        self.display = display
        self.config = config
        self.translation_delay = translation_delay  # 未完成句子的翻译延迟（秒）

        self.audio_config = audio_capture.config
        self._window_buffer = []
        self._last_text = ""
        self._last_completed_text = ""  # 记录最近完成的句子，避免重复
        self._translation_queue: queue.Queue = queue.Queue()
        self._running = False
        self._pending_translation_timer: Optional[threading.Timer] = None
        self._pending_translation_text: str = ""
        self._timer_lock = threading.Lock()
        self._silence_count = 0  # 连续静音计数·
        self._has_speech = False  # 当前是否有语音输入

    def _start_translation_worker(self):
        """启动异步翻译线程"""

        def worker():
            while self._running:
                try:
                    text = self._translation_queue.get(timeout=1)
                    # 获取历史上下文
                    context = self.display.get_context_for_translation()
                    # 翻译时传递上下文
                    translated = self.translator.translate(text, context=context)
                    self.display.update_translated(translated)
                except queue.Empty:
                    continue
                except Exception as e:
                    self.display.print(f"[red]翻译错误: {e}[/red]")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread

    def _cancel_pending_translation(self):
        """取消待处理的翻译定时器"""
        with self._timer_lock:
            if self._pending_translation_timer:
                self._pending_translation_timer.cancel()
                self._pending_translation_timer = None
                self._pending_translation_text = ""

    def _schedule_delayed_translation(self, text: str):
        """延迟翻译（用于未完成的句子）"""

        def do_translation():
            with self._timer_lock:
                if self._pending_translation_text == text:
                    self._translation_queue.put(text)
                    self._pending_translation_text = ""
                    self._pending_translation_timer = None

        with self._timer_lock:
            # 取消之前的定时器
            if self._pending_translation_timer:
                self._pending_translation_timer.cancel()

            # 创建新的定时器
            self._pending_translation_text = text
            self._pending_translation_timer = threading.Timer(
                self.translation_delay, do_translation
            )
            self._pending_translation_timer.daemon = True
            self._pending_translation_timer.start()

    def _handle_transcription_result(self, text: str, is_final: bool = False) -> bool:
        """处理转录结果

        Args:
            text: 转录文本
            is_final: 是否是完整句子（由静音检测决定）
        """
        if not text:
            return False

        # 如果与上次完全相同，跳过
        if text == self._last_text and not is_final:
            return False

        # 如果是完整句子（由静音检测判定）
        if is_final:
            # 检查是否与最近完成的句子相同，避免重复
            if text == self._last_completed_text:
                return False

            self._cancel_pending_translation()  # 取消任何待处理的翻译
            self._last_completed_text = text  # 记录完成的句子
            # 完整句子，创建新条目
            self.display.update_original(text, is_final=True)
            self._translation_queue.put(text)  # 立即翻译
            return True

        # 未完成句子，检查是否有显著变化
        if self._last_text:
            # 如果新文本比旧文本短很多，说明是新句子开始，finalize旧句子
            if len(text) < len(self._last_text) * 0.5:
                print(f"[DEBUG] 检测到新句子（文本变短），finalize旧句子: {self._last_text[:30]}...")
                # 先finalize旧句子
                self.display.update_original(self._last_text, is_final=True)
                self._translation_queue.put(self._last_text)
                self._last_completed_text = self._last_text
                # 然后开始新句子
                self._last_text = text
                self.display.update_original(text, is_final=False)
                self._schedule_delayed_translation(text)
                return True

            # 如果开头差异很大（前30%不同），说明是新句子，finalize旧句子
            compare_len = min(len(text), len(self._last_text), max(10, int(len(self._last_text) * 0.3)))
            if not text[:compare_len] == self._last_text[:compare_len]:
                print(f"[DEBUG] 检测到新句子（开头不同），finalize旧句子: {self._last_text[:30]}...")
                # 先finalize旧句子
                self.display.update_original(self._last_text, is_final=True)
                self._translation_queue.put(self._last_text)
                self._last_completed_text = self._last_text
                # 然后开始新句子
                self._last_text = text
                self.display.update_original(text, is_final=False)
                self._schedule_delayed_translation(text)
                return True

        # 更新为新的未完成句子，更新现有条目
        self._last_text = text
        self.display.update_original(text, is_final=False)
        # 不立即翻译，而是使用延迟翻译
        self._schedule_delayed_translation(text)
        return True

    def _is_silence(self, audio: np.ndarray) -> bool:
        """检查是否为静音"""
        return np.abs(audio).max() < self.config.silence_threshold

    def _process_audio_chunk(self):
        """处理音频块"""
        print(f"[DEBUG] _process_audio_chunk 被调用")
        samples_per_interval = int(
            self.audio_config.sample_rate * self.config.process_interval
        )
        window_samples = int(
            self.audio_config.sample_rate * self.config.window_duration
        )

        # 合并音频（保留窗口大小的数据）
        audio = np.concatenate(self._window_buffer).flatten().astype(np.float32)
        print(f"[DEBUG] 音频长度: {len(audio)}, max值: {np.abs(audio).max():.6f}")

        # 保持滑动窗口大小，移除旧数据
        if len(audio) > window_samples:
            overlap_samples = window_samples - samples_per_interval
            audio = audio[-window_samples:]
            # 重建buffer（只保留重叠部分）
            self._window_buffer = [audio[-overlap_samples:].reshape(-1, 1)]

        # 检查是否为静音
        is_silent = self._is_silence(audio)
        print(f"[DEBUG] 是否静音: {is_silent}, 阈值: {self.config.silence_threshold}")

        if is_silent:
            # 静音时，增加静音计数
            self._silence_count += 1
            print(f"[DEBUG] 静音计数: {self._silence_count}, 有语音: {self._has_speech}, 有文本: {bool(self._last_text)}")

            # 如果连续静音超过阈值（例如2个周期，约1.6秒），并且之前有语音和文本
            # 说明句子说完了，标记为完整句子
            if self._silence_count >= 2 and self._has_speech and self._last_text:
                print(f"[DEBUG] 触发finalize: {self._last_text[:50]}...")
                self._handle_transcription_result(self._last_text, is_final=True)
                self._has_speech = False
                self._last_text = ""
            return

        # 有声音时，重置静音计数
        if self._silence_count > 0:
            print(f"[DEBUG] 重置静音计数，之前计数: {self._silence_count}")
        self._silence_count = 0
        self._has_speech = True

        # Whisper 转录
        segments, _ = self.transcriber.transcribe(audio)

        # 提取转录文本并处理
        text = self.transcriber.segments_to_text(segments)
        self._handle_transcription_result(text, is_final=False)

    def run(self):
        """运行音频处理循环"""
        self._running = True
        self._start_translation_worker()

        samples_per_interval = int(
            self.audio_config.sample_rate * self.config.process_interval
        )

        while self._running:
            try:
                data = self.audio_capture.audio_queue.get(timeout=1)
                self._window_buffer.append(data)

                # 计算当前缓冲区大小
                total_samples = sum(len(b) for b in self._window_buffer)

                # 达到处理间隔，进行转录
                if total_samples >= samples_per_interval:
                    self._process_audio_chunk()

            except queue.Empty:
                continue
            except Exception as e:
                self.display.print(f"[red]处理错误: {e}[/red]")

    def stop(self):
        """停止处理"""
        self._running = False
        self._cancel_pending_translation()
