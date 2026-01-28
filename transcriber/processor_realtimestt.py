"""音频处理器模块 - 基于 RealtimeSTT"""

import difflib
import queue
import threading
import time
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
        self._last_processed_text = ""  # 最近一次处理的文本（用于相似度比较）

        # 实时翻译触发控制
        self._last_realtime_text = ""
        self._realtime_update_count = 0
        self._last_realtime_update_time = 0.0
        self._realtime_translation_pending = False

        # 配置参数
        self.REALTIME_TEXT_MIN_LENGTH = 20  # 触发翻译的最小长度
        self.REALTIME_UPDATE_THRESHOLD = 3  # 连续更新多少次触发翻译
        self.REALTIME_IDLE_THRESHOLD = 1.0  # 停止更新多久触发翻译（秒）
        self.SIMILARITY_THRESHOLD = 0.85  # 相似度阈值（0-1）

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

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度（0-1）

        Args:
            text1: 第一个文本
            text2: 第二个文本

        Returns:
            float: 相似度分数 (0-1)，1 表示完全相同
        """
        if not text1 or not text2:
            return 0.0

        # 使用 SequenceMatcher 计算相似度
        # ratio() 返回 0-1 的相似度分数
        matcher = difflib.SequenceMatcher(None, text1.lower(), text2.lower())
        return matcher.ratio()

    def _start_translation_worker(self):
        """启动异步翻译线程 - 支持完整句子和实时文本翻译"""

        def worker():
            while self._running:
                try:
                    # 从队列获取翻译任务
                    task = self._translation_queue.get(timeout=1)
                    text, is_completed = task

                    if is_completed:
                        # 完整句子：从数据库获取新句子并翻译
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

                    else:
                        # 实时文本：直接翻译，只更新 Overlay，不存数据库
                        print(f"[DEBUG] 开始翻译实时文本: {text}...")
                        try:
                            # 获取翻译上下文
                            context = self.display.get_context_for_translation()
                            # 翻译实时文本
                            translation = self.translator.translate(text, context=context)
                            print(f"[DEBUG] 实时翻译完成: {translation}...")
                            # 更新 Overlay 显示
                            self.display.update_realtime_translation(translation)
                        except Exception as e:
                            print(f"[DEBUG] 实时翻译失败: {e}")
                        finally:
                            # 重置待处理标记
                            self._realtime_translation_pending = False

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
        """稳定转录回调 - 用于悬浮窗显示

        注：实时文本翻译触发已禁用，只有完整句子才触发翻译。
        保留了智能触发框架，如果将来需要启用，只需取消注释相关代码。

        智能触发逻辑（参考 LiveCaptions-Translator）：
        1. 文本长度 >= 20 字符 且 连续更新 3 次 → 可触发翻译
        2. 文本停止更新 >= 1.0 秒 → 可触发翻译
        """
        print(f"\n[DEBUG] ========== _on_stabilized_update 被调用 ==========")
        print(f"[DEBUG] 完整文本: {text}")
        print(f"[DEBUG] 长度: {len(text) if text else 0} 字符")

        if not text:
            return

        # 更新实时文本跟踪并智能触发翻译
        current_time = time.time()
        text_changed = text != self._last_realtime_text

        if text_changed:
            self._realtime_update_count += 1
            self._last_realtime_update_time = current_time
            self._last_realtime_text = text
            print(f"[DEBUG] 文本更新 #{self._realtime_update_count}, 长度: {len(text)}")

            # 触发条件 1: 文本够长 且 连续更新次数达到阈值
            if (len(text) >= self.REALTIME_TEXT_MIN_LENGTH and
                self._realtime_update_count >= self.REALTIME_UPDATE_THRESHOLD and
                not self._realtime_translation_pending):
                print(f"[DEBUG] 触发实时翻译（连续更新 {self._realtime_update_count} 次）")
                self._trigger_realtime_translation(text)
        else:
            # 触发条件 2: 文本停止更新超过阈值时间
            idle_time = current_time - self._last_realtime_update_time
            if (idle_time >= self.REALTIME_IDLE_THRESHOLD and
                len(text) >= self.REALTIME_TEXT_MIN_LENGTH and
                not self._realtime_translation_pending):
                print(f"[DEBUG] 触发实时翻译（空闲 {idle_time:.2f} 秒）")
                self._trigger_realtime_translation(text)

        print(f"[DEBUG] ===============================================\n")

        self._last_text = text
        # 直接更新 Overlay 窗口，不影响数据库和主窗口
        self.display.update_overlay_only(text)

    def _trigger_realtime_translation(self, text: str):
        """触发实时文本的翻译

        Args:
            text: 要翻译的文本
        """
        # 标记有待翻译的实时文本
        self._realtime_translation_pending = True

        # 将文本放入翻译队列（is_realtime=True 表示是实时文本，不是完整句子）
        self._translation_queue.put((text, False))

        print(f"[DEBUG] 实时文本已加入翻译队列: {text[:50]}...")

    def _reset_realtime_state(self):
        """重置实时翻译状态（在完整句子到来时调用）"""
        self._last_realtime_text = ""
        self._realtime_update_count = 0
        self._last_realtime_update_time = 0.0
        self._realtime_translation_pending = False

    def _handle_completed_sentence(self, text: str):
        """处理完整句子（从 recorder.text() 返回）

        使用相似度算法去重，避免 "Hello" → "Hello world" 被当作两句话
        """
        if not text or not text.strip():
            return

        # 重置实时翻译状态（完整句子到来，清空实时状态）
        self._reset_realtime_state()

        # 相似度去重检查
        is_duplicate = False
        if self._last_processed_text:
            similarity = self._calculate_similarity(text, self._last_processed_text)
            print(f"[DEBUG] 与上次文本相似度: {similarity:.2f}")

            if similarity >= self.SIMILARITY_THRESHOLD:
                is_duplicate = True
                print(f"[DEBUG] 相似度过高 ({similarity:.2f} >= {self.SIMILARITY_THRESHOLD})，判定为重复")
                print(f"[DEBUG] 上次: {self._last_processed_text}")
                print(f"[DEBUG] 本次: {text}")

        if is_duplicate:
            print(f"[DEBUG] 跳过重复文本")
            return

        # 不是重复，记录并处理
        self._last_processed_text = text
        self._last_completed_text = text
        self._last_text = ""

        # 添加到已处理集合（保留原有的精确匹配检查作为辅助）
        self._processed_sentences.add(text)

        # 限制去重集合大小，只保留最近 1000 条（防止内存无限增长）
        if len(self._processed_sentences) > 1000:
            # 保留最新加入的 800 条
            texts_list = list(self._processed_sentences)
            self._processed_sentences = set(texts_list[-800:])

        print(f"[DEBUG] 新文本，添加到主窗口显示")
        print(f"[DEBUG] 已处理总数: {len(self._processed_sentences)}")

        # 添加到显示（作为一条完整记录）
        self.display.add_completed_sentences([text])
        # 立即翻译
        self._translation_queue.put((text, True))

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
