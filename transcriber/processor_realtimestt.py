"""音频处理器模块 - 基于 RealtimeSTT"""

import queue
import re
import threading
from typing import Optional

import sounddevice as sd
from RealtimeSTT import AudioToTextRecorder

from .translation import Translator


class RealtimeSTTProcessor:
    """基于 RealtimeSTT 的音频处理器"""

    def __init__(
        self,
        translator: Translator,
        display,
        model: str = "tiny",
        language: str = "en",
        device: str = "cpu",
        compute_type: str = "int8",
        translation_delay: float = 2.0,
        audio_device_name: str = "BlackHole 2ch",
    ):
        self.translator = translator
        self.display = display
        self.translation_delay = translation_delay

        self._last_text = ""
        self._last_completed_text = ""
        self._translation_queue: queue.Queue = queue.Queue()
        self._running = False
        self._pending_translation_timer: Optional[threading.Timer] = None
        self._pending_translation_text: str = ""
        self._timer_lock = threading.Lock()

        # 查找音频设备索引
        device_index = self._find_audio_device(audio_device_name)
        if device_index is None:
            raise RuntimeError(f"未找到音频设备: {audio_device_name}")

        # 初始化 RealtimeSTT recorder
        self.recorder = AudioToTextRecorder(
            model=model,
            language=language,
            device=device,
            compute_type=compute_type,
            input_device_index=device_index,  # 指定音频输入设备
            # VAD 配置
            silero_sensitivity=0.3,  # VAD 灵敏度 (0-1, 越大越敏感)
            webrtc_sensitivity=3,  # WebRTC VAD 灵敏度 (0-3)
            post_speech_silence_duration=0.4,  # 句子结束后的静音时长（秒）
            min_length_of_recording=0.5,  # 最小录音长度（秒）
            min_gap_between_recordings=0.0,  # 录音之间的最小间隔
            enable_realtime_transcription=True,  # 启用实时转录
            realtime_processing_pause=0.1,  # 实时处理间隔
            on_realtime_transcription_update=self._on_realtime_update,
        )

    def _find_audio_device(self, device_name: str) -> Optional[int]:
        """查找音频设备索引"""
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if device_name in dev["name"] and dev["max_input_channels"] > 0:
                return i
        return None

    def _start_translation_worker(self):
        """启动异步翻译线程"""

        def worker():
            while self._running:
                try:
                    # 从队列获取翻译任务（段落翻译）
                    _ = self._translation_queue.get(timeout=1)

                    # 获取当前所有句子
                    sentences = self.display.gui.get_sentences()
                    if not sentences:
                        continue

                    # 合并成段落
                    paragraph = " ".join(sentences)

                    # 翻译整个段落（不需要上下文，因为段落本身就是上下文）
                    translated = self.translator.translate(paragraph, context=[])

                    # 更新段落翻译
                    self.display.update_translated_with_original("", translated)
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
                    self._translation_queue.put((text, False))  # (original_text, is_final)
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

    def _on_realtime_update(self, text: str):
        """实时转录更新回调（句子未完成）"""
        if not text or text == self._last_text:
            return

        self._last_text = text
        # 未完成的句子，更新当前显示
        self.display.update_original(text, is_final=False)
        # 延迟翻译
        self._schedule_delayed_translation(text)

    def _split_sentences(self, text: str) -> list[str]:
        """将文本分割成句子列表

        使用简单的句号、问号、感叹号分割，同时保留缩写词（如 Mr. Dr.）
        """
        # 简单分割：按 .!? 分割，但要考虑常见缩写
        # 使用正则表达式分割句子
        sentences = re.split(r'(?<=[.!?])\s+', text)
        # 过滤掉空句子
        return [s.strip() for s in sentences if s.strip()]

    def _handle_completed_sentence(self, text: str):
        """处理完成的句子（可能包含多个句子）"""
        if not text or not text.strip():
            return

        # 检查是否与最近完成的句子相同，避免重复
        if text == self._last_completed_text:
            return

        self._cancel_pending_translation()
        self._last_completed_text = text
        self._last_text = ""

        # 将文本分割成多个句子
        sentences = self._split_sentences(text)

        # 批量添加句子到显示中
        self.display.add_completed_sentences(sentences)

        # 立即翻译整个段落
        self._translation_queue.put((text, True))  # (original_text, is_final)

    def run(self):
        """运行音频处理循环"""
        self._running = True
        self._start_translation_worker()

        try:
            # RealtimeSTT 的 text() 方法会阻塞，直到检测到完整句子
            # 实时更新通过 on_realtime_transcription_update 回调
            while self._running:
                # text() 返回完整的句子
                full_text = self.recorder.text()
                if full_text:
                    self._handle_completed_sentence(full_text)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        """停止处理"""
        self._running = False
        self._cancel_pending_translation()
        try:
            if hasattr(self.recorder, "abort"):
                self.recorder.abort()
            if hasattr(self.recorder, "shutdown"):
                self.recorder.shutdown()
        except Exception as e:
            print(f"停止 recorder 时出错: {e}")
