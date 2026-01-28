"""音频处理器模块 - 基于 RealtimeSTT"""

import queue
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
        audio_device_name: str = "BlackHole 2ch",
    ):
        self.translator = translator
        self.display = display

        self._last_text = ""
        self._last_completed_text = ""
        self._translation_queue: queue.Queue = queue.Queue()
        self._running = False

        # 跟踪已处理的文本（用于去重）
        self._processed_sentences: set[str] = set()

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
            on_realtime_transcription_stabilized=self._on_stabilized_update,  # 悬浮窗显示（稳定文本）
        )

    def _find_audio_device(self, device_name: str) -> Optional[int]:
        """查找音频设备索引"""
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if device_name in dev["name"] and dev["max_input_channels"] > 0:
                return i
        return None

    def _start_translation_worker(self):
        """启动异步翻译线程 - 逐句翻译模式"""

        def worker():
            while self._running:
                try:
                    # 从队列获取翻译任务
                    _ = self._translation_queue.get(timeout=1)

                    # 检查是否有新句子需要翻译
                    new_sentences = self.display.get_new_sentences_for_translation()
                    if not new_sentences:
                        continue

                    # 逐句翻译新句子
                    translations = []
                    for sentence_id, original_text in new_sentences:
                        try:
                            # 获取翻译上下文（最近N句已翻译的句子）
                            context = self.display.get_context_for_translation()
                            # 翻译单句
                            translation = self.translator.translate(original_text, context=context)
                            translations.append((sentence_id, translation))
                        except Exception as e:
                            print(f"翻译失败: {original_text[:100]}... 错误: {e}")

                    # 批量更新翻译
                    if translations:
                        self.display.batch_update_translations(translations)

                except queue.Empty:
                    continue
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    self.display.print(f"翻译错误: {e}")
                    print(f"翻译错误详情:\n{error_details}")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread

    def _on_stabilized_update(self, text: str):
        """稳定转录回调 - 仅用于悬浮窗（高质量、稳定的文本）"""
        print(f"\n[DEBUG] ========== _on_stabilized_update 被调用 ==========")
        print(f"[DEBUG] 完整文本: {text}")
        print(f"[DEBUG] 长度: {len(text) if text else 0} 字符")
        print(f"[DEBUG] ===============================================\n")

        if not text or text == self._last_text:
            return

        self._last_text = text
        # 直接更新 Overlay 窗口，不影响数据库和主窗口
        self.display.update_overlay_only(text)

    def _handle_completed_sentence(self, text: str):
        """处理完整句子（从 recorder.text() 返回）"""
        if not text or not text.strip():
            return

        # 检查是否与最近完成的句子相同，避免重复
        if text == self._last_completed_text:
            print(f"[DEBUG] 跳过重复文本（与上次相同）")
            return

        self._last_completed_text = text
        self._last_text = ""

        # 去重检查
        if text not in self._processed_sentences:
            print(f"[DEBUG] 新文本，添加到主窗口显示")
            self._processed_sentences.add(text)

            # 限制去重集合大小，只保留最近 1000 条（防止内存无限增长）
            if len(self._processed_sentences) > 1000:
                # 保留最新加入的 800 条
                texts_list = list(self._processed_sentences)
                self._processed_sentences = set(texts_list[-800:])

            print(f"[DEBUG] 已处理总数: {len(self._processed_sentences)}")

            # 添加到显示（作为一条完整记录）
            self.display.add_completed_sentences([text])
            # 立即翻译
            self._translation_queue.put((text, True))
        else:
            print(f"[DEBUG] 重复文本(已跳过): {text}")

    def run(self):
        """运行音频处理循环"""
        self._running = True
        self._start_translation_worker()

        try:
            # 使用 recorder.text() 获取完整句子（在 VAD 检测到句子结束后返回）
            while self._running:
                # text() 会阻塞直到检测到句子结束
                text_from_method = self.recorder.text()
                if text_from_method:
                    print(f"\n[DEBUG] ========== recorder.text() 返回完整句子 ==========")
                    print(f"[DEBUG] 完整文本: {text_from_method}")
                    print(f"[DEBUG] 长度: {len(text_from_method)} 字符")
                    print(f"[DEBUG] ===============================================\n")

                    # 处理完整句子：去重并添加到主窗口
                    self._handle_completed_sentence(text_from_method)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        """停止处理"""
        self._running = False
        try:
            if hasattr(self.recorder, "abort"):
                self.recorder.abort()
            if hasattr(self.recorder, "shutdown"):
                self.recorder.shutdown()
        except Exception as e:
            print(f"停止 recorder 时出错: {e}")
