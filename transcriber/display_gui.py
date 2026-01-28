"""GUI 显示模块 - 基于 Tkinter"""

import tkinter as tk
from tkinter import scrolledtext, ttk
import threading


class SubtitleGUI:
    """字幕 GUI 显示器"""

    def __init__(self, max_visible_items: int = 6):
        self.root = tk.Tk()
        self.root.title("🎤 实时字幕 + 翻译")
        self.root.geometry("700x600")
        self.root.configure(bg="#f5f5f5")

        # 最多保留多少句话
        self.max_sentences = max_visible_items

        # 段落模式：维护最近的句子列表
        self.sentences = []  # 已完成的句子列表（最多max_sentences个）
        self.current_sentence = ""  # 当前正在说的句子
        self.paragraph_translation = ""  # 整个段落的翻译

        self._lock = threading.Lock()

        # 创建主容器
        self._setup_ui()

    def _setup_ui(self):
        """设置 UI"""
        # 顶部状态栏
        self.status_frame = ttk.Frame(self.root, padding=10)
        self.status_frame.pack(fill="x", side="top")

        self.status_label = ttk.Label(
            self.status_frame,
            text="🟢 正在监听...",
            font=("Arial", 10, "bold"),
            foreground="#4CAF50",
        )
        self.status_label.pack(side="left")

        # 分隔线
        separator = ttk.Separator(self.root, orient="horizontal")
        separator.pack(fill="x", pady=5)

        # 创建主字幕显示框（使用Text widget）
        text_frame = ttk.Frame(self.root)
        text_frame.pack(fill="both", expand=True, padx=15, pady=10)

        # 创建带滚动条的文本框
        self.subtitle_text = tk.Text(
            text_frame,
            wrap="word",
            font=("Arial", 12),
            bg="white",
            fg="#333333",
            relief="solid",
            borderwidth=1,
            padx=15,
            pady=15,
            state="disabled",  # 只读
        )

        scrollbar = ttk.Scrollbar(text_frame, command=self.subtitle_text.yview)
        self.subtitle_text.configure(yscrollcommand=scrollbar.set)

        self.subtitle_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 配置文本标签样式 - YouTube字幕风格：更大更清晰
        self.subtitle_text.tag_configure("original", foreground="#2196F3", font=("Arial", 14, "bold"))
        self.subtitle_text.tag_configure("translation", foreground="#4CAF50", font=("Arial", 13, "normal"))
        self.subtitle_text.tag_configure("loading", foreground="#9E9E9E", font=("Arial", 12, "italic"))

        # 鼠标滚轮支持
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        """处理鼠标滚轮"""
        self.subtitle_text.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _refresh_display(self):
        """刷新整个显示内容 - 段落模式"""
        # 清空文本框
        self.subtitle_text.configure(state="normal")
        self.subtitle_text.delete("1.0", "end")

        # 构建完整的原文段落（已完成的句子 + 当前句子）
        all_sentences = self.sentences.copy()
        if self.current_sentence:
            all_sentences.append(self.current_sentence)


        if not all_sentences:
            # 如果没有任何内容，显示等待提示
            self.subtitle_text.insert("end", "等待语音输入...", "loading")
        else:
            # 显示原文段落
            self.subtitle_text.insert("end", "🎤 ", "original")
            original_paragraph = " ".join(all_sentences)
            self.subtitle_text.insert("end", original_paragraph + "\n\n", "original")

            # 显示翻译段落
            if self.paragraph_translation:
                self.subtitle_text.insert("end", "🌍 ", "translation")
                self.subtitle_text.insert("end", self.paragraph_translation, "translation")
            else:
                self.subtitle_text.insert("end", "🌍 ", "loading")
                self.subtitle_text.insert("end", "⏳ 翻译中...", "loading")

        # 设置为只读
        self.subtitle_text.configure(state="disabled")

        # 自动滚动到底部显示最新内容
        self.subtitle_text.see("end")

    def update_current(self, original_text: str, translation_text: str = ""):
        """更新当前正在说的句子"""
        with self._lock:
            self.current_sentence = original_text
            # 刷新显示
            self._refresh_display()

    def finalize_current(self):
        """把当前句子固定到句子列表中"""
        with self._lock:
            if self.current_sentence:
                # 添加到句子列表
                self.sentences.append(self.current_sentence)

                # 如果超过最大数量，移除最旧的
                if len(self.sentences) > self.max_sentences:
                    self.sentences.pop(0)

                # 清空当前句子
                self.current_sentence = ""

                # 刷新显示
                self._refresh_display()

    def add_sentences(self, new_sentences: list[str]):
        """批量添加多个句子到句子列表

        Args:
            new_sentences: 要添加的句子列表
        """
        with self._lock:
            # 添加所有新句子
            self.sentences.extend(new_sentences)

            # 如果超过最大数量，只保留最新的max_sentences个
            if len(self.sentences) > self.max_sentences:
                self.sentences = self.sentences[-self.max_sentences:]

            # 刷新显示
            self._refresh_display()

    def update_paragraph_translation(self, translation: str):
        """更新整个段落的翻译"""
        with self._lock:
            self.paragraph_translation = translation
            # 刷新显示
            self._refresh_display()

    def get_sentences(self) -> list[str]:
        """获取当前所有句子（包括未完成的）"""
        with self._lock:
            all_sentences = self.sentences.copy()
            if self.current_sentence:
                all_sentences.append(self.current_sentence)
            return all_sentences

    def update_status(self, status: str, color: str = "#4CAF50"):
        """更新状态栏"""
        self.status_label.config(text=status, foreground=color)

    def run(self):
        """运行 GUI 主循环"""
        self.root.mainloop()

    def quit(self):
        """退出 GUI"""
        self.root.quit()
        self.root.destroy()


class SubtitleGUIDisplay:
    """字幕 GUI 显示适配器（兼容原有接口）"""

    def __init__(self, max_visible_items: int = 6, context_size: int = 10):
        """初始化

        Args:
            max_visible_items: GUI显示的最大句子数量
            context_size: 传递给LLM的上下文句子数量（段落模式下不使用）
        """
        self.gui = SubtitleGUI(max_visible_items=max_visible_items)
        self._current_original = None
        self._is_current_final = False
        self.context_size = context_size

    def get_context_for_translation(self, context_size: int | None = None) -> list[tuple[str, str]]:
        """获取用于翻译的历史上下文（段落模式：返回空列表，因为翻译整个段落）

        Returns:
            [] 空列表（段落模式不需要上下文）
        """
        # 段落模式下不需要返回上下文，因为我们翻译的是整个段落
        return []

    def update_original(self, text: str, is_final: bool = False):
        """更新原文

        Args:
            text: 原文文本
            is_final: 是否是完整句子（True时固定当前句子，False时更新当前句子）
        """
        self._current_original = text
        self._is_current_final = is_final

        if is_final:
            # 完整句子，先更新current，然后立即finalize
            self.gui.root.after(0, lambda t=text: self.gui.update_current(t))
            self.gui.root.after(10, lambda: self.gui.finalize_current())
        else:
            # 未完成句子，更新当前句子
            self.gui.root.after(0, lambda t=text: self.gui.update_current(t))

    def add_completed_sentences(self, sentences: list[str]):
        """批量添加多个已完成的句子

        Args:
            sentences: 已完成的句子列表
        """
        self.gui.root.after(0, lambda s=sentences: self.gui.add_sentences(s))

    def update_translated(self, text: str):
        """更新翻译（使用当前记录的原文）"""
        # 段落模式：直接更新整个段落的翻译
        self.update_translated_with_original("", text)

    def update_translated_with_original(self, original_text: str, translation: str):
        """更新翻译（段落模式：翻译整个段落）"""
        def do_update():
            # 段落模式：直接更新段落翻译
            self.gui.update_paragraph_translation(translation)

        self.gui.root.after(0, do_update)

    def print(self, message: str, style: str = ""):
        """打印消息到状态栏"""
        # 简单处理 rich 样式标记
        clean_message = message.replace("[bold]", "").replace("[/bold]", "")
        clean_message = clean_message.replace("[green]", "").replace("[/green]", "")
        clean_message = clean_message.replace("[yellow]", "").replace("[/yellow]", "")
        clean_message = clean_message.replace("[red]", "").replace("[/red]", "")

        color = "#4CAF50"
        if "错误" in message or "error" in message.lower():
            color = "#F44336"
        elif "警告" in message or "warning" in message.lower():
            color = "#FF9800"

        self.gui.root.after(0, lambda: self.gui.update_status(clean_message, color))

    def run(self):
        """运行 GUI"""
        self.gui.run()

    def quit(self):
        """退出"""
        self.gui.quit()


class SubtitleDisplayCoordinator:
    """双窗口显示协调器

    整合 Overlay 窗口和主窗口，统一管理数据和显示。
    保持与 SubtitleGUIDisplay 相同的接口，便于集成。
    """

    def __init__(self, max_visible_items: int = 6, context_size: int = 10):
        """初始化

        Args:
            max_visible_items: 最大显示句子数（兼容性参数，实际由 DataManager 控制）
            context_size: 上下文大小（兼容性参数，段落模式不使用）
        """
        import time
        from .data_manager import DataManager
        from .main_window import MainWindow
        from .overlay_window import OverlayWindow

        # 记录当前会话开始时间（用于 Overlay 过滤历史数据）
        self._session_start_time = time.time()

        # 数据层
        self.data_manager = DataManager()

        # 显示层
        self.main_window = MainWindow(self.data_manager)
        self.overlay_window = OverlayWindow(
            self.main_window.root,
            self.data_manager
        )

        # 设置主窗口的 overlay 引用
        self.main_window.set_overlay_window(self.overlay_window)

        # 兼容性：提供 gui 属性，指向主窗口
        self.gui = self.main_window

        # 当前句子的状态
        self._current_sentence_id = None
        self._current_original = ""
        self._new_sentence_ids = []  # 新添加的句子ID列表（用于翻译）
        self._has_new_content = False  # 标记是否有新内容（用于 Overlay 空白启动）

        # 兼容性参数
        self.context_size = context_size

        # 延迟初始化显示（等待窗口完全创建）
        self.main_window.root.after(100, self._initial_refresh)

    def get_context_for_translation(self, context_size: int | None = None) -> list[tuple[str, str]]:
        """获取翻译上下文（逐句翻译模式：返回最近N句已翻译的句子）

        Args:
            context_size: 上下文句子数量，如果为None则使用默认值

        Returns:
            list[tuple[str, str]]: [(original, translation), ...] 最近的已翻译句子
        """
        if context_size is None:
            context_size = self.context_size

        all_sentences = self.data_manager.get_all_sentences()

        # 获取最近N句已翻译的句子
        context = []
        for sentence in reversed(all_sentences):
            if sentence.translation and sentence.translation.strip():
                context.append((sentence.original, sentence.translation))
                if len(context) >= context_size:
                    break

        # 反转回正序
        return list(reversed(context))

    def get_sentences(self) -> list[str]:
        """获取当前所有句子的原文列表（兼容旧代码）

        Returns:
            list[str]: 所有句子的原文
        """
        all_sentences = self.data_manager.get_all_sentences()
        return [s.original for s in all_sentences]

    def get_new_sentences_for_translation(self) -> list[tuple[str, str]]:
        """获取需要翻译的新句子（ID + 原文）

        Returns:
            list[tuple[str, str]]: [(sentence_id, original_text), ...]
        """
        if not self._new_sentence_ids:
            return []

        result = []
        all_sentences = self.data_manager.get_all_sentences()

        # 找到对应的句子
        for sentence in all_sentences:
            if sentence.id in self._new_sentence_ids:
                result.append((sentence.id, sentence.original))

        # 清空新句子列表
        self._new_sentence_ids = []

        return result

    def get_current_incomplete_sentence(self) -> tuple[str, str] | None:
        """获取当前未完成的句子（用于延迟翻译）

        Returns:
            tuple[str, str] | None: (sentence_id, original_text) 或 None
        """
        if not self._current_sentence_id:
            return None

        all_sentences = self.data_manager.get_all_sentences()
        for sentence in all_sentences:
            if sentence.id == self._current_sentence_id:
                return (sentence.id, sentence.original)

        return None

    def update_overlay_only(self, text: str):
        """仅更新 Overlay 窗口（用于实时显示，不影响数据库）

        Args:
            text: 实时文本（未完成的句子）
        """
        if not text:
            return

        def do_update():
            # 直接更新 Overlay 窗口的文本显示
            self.overlay_window.update_realtime_text(text)

        # 调度到主线程
        self.main_window.root.after(0, do_update)

    def update_original(self, text: str, is_final: bool = False):
        """更新原文

        Args:
            text: 原文文本
            is_final: 是否是完整句子
        """
        self._current_original = text
        self._has_new_content = True  # 标记有新内容

        if is_final:
            # 完整句子：添加到数据库
            if text.strip():
                record = self.data_manager.add_sentence(
                    original=text,
                    translation="",
                    is_completed=True
                )
                self._current_sentence_id = record.id
                # 标记为新句子，需要翻译
                self._new_sentence_ids = [record.id]

                # 刷新两个窗口
                self._refresh_both_windows()
        else:
            # 未完成句子：更新或创建临时记录
            if not self._current_sentence_id:
                # 创建新的未完成句子
                record = self.data_manager.add_sentence(
                    original=text,
                    translation="",
                    is_completed=False
                )
                self._current_sentence_id = record.id
            else:
                # 更新现有未完成句子
                self.data_manager.update_sentence(
                    self._current_sentence_id,
                    original=text
                )

            # 刷新两个窗口
            self._refresh_both_windows()

    def add_completed_sentences(self, sentences: list[str]):
        """批量添加完整句子

        Args:
            sentences: 已完成的句子列表
        """
        self._has_new_content = True  # 标记有新内容

        # 如果有当前未完成的句子，先标记为完成
        if self._current_sentence_id:
            self.data_manager.update_sentence(
                self._current_sentence_id,
                is_completed=True
            )
            self._current_sentence_id = None

        # 批量添加新句子，并返回新句子的ID列表
        new_sentence_ids = []
        for sentence in sentences:
            if sentence.strip():
                record = self.data_manager.add_sentence(
                    original=sentence,
                    translation="",
                    is_completed=True
                )
                new_sentence_ids.append(record.id)

        # 保存新句子ID，供翻译使用
        self._new_sentence_ids = new_sentence_ids

        # 刷新两个窗口
        self._refresh_both_windows()

    def update_translated(self, text: str):
        """更新翻译（使用当前原文）

        Args:
            text: 翻译文本
        """
        self.update_translated_with_original(self._current_original, text)

    def update_translated_with_original(self, original_text: str, translation: str):
        """更新翻译（段落模式：更新最新句子的翻译）

        Args:
            original_text: 原文（兼容性参数）
            translation: 翻译文本
        """
        # 获取最新的句子
        all_sentences = self.data_manager.get_all_sentences()

        if all_sentences:
            # 更新最新句子的翻译
            latest = all_sentences[-1]
            self.data_manager.update_sentence(
                latest.id,
                translation=translation
            )

            # 刷新两个窗口
            self._refresh_both_windows()

    def batch_update_translations(self, sentence_translations: list[tuple[str, str]]):
        """批量更新多个句子的翻译

        Args:
            sentence_translations: [(sentence_id, translation), ...]
        """
        for sentence_id, translation in sentence_translations:
            self.data_manager.update_sentence(
                sentence_id,
                translation=translation
            )

        # 批量更新后刷新窗口
        self._refresh_both_windows()

    def _initial_refresh(self):
        """初始化时刷新显示（延迟调用，确保窗口已创建）"""
        # Overlay 窗口：启动时显示空白
        self.overlay_window.update_display([])

        # 主窗口：显示历史记录
        all_sentences = self.data_manager.get_all_sentences()
        self.main_window.update_history(all_sentences)

    def _refresh_both_windows(self):
        """刷新两个窗口的显示"""
        def do_refresh():
            # Overlay 窗口：只显示当前会话的新内容（不包括历史）
            if self._has_new_content:
                # 只获取当前会话开始后的句子
                recent_sentences = self.data_manager.get_recent_sentences_after(
                    self._session_start_time, count=4
                )
                self.overlay_window.update_display(recent_sentences)
            else:
                # 启动时显示空白
                self.overlay_window.update_display([])

            # 主窗口：始终显示全部（包括历史）
            all_sentences = self.data_manager.get_all_sentences()
            self.main_window.update_history(all_sentences)

        # 调度到主线程
        self.main_window.root.after(0, do_refresh)

    def print(self, message: str, style: str = ""):
        """打印消息到状态栏

        Args:
            message: 消息文本
            style: 样式（兼容性参数）
        """
        # 清理 rich 样式标记
        clean_message = message.replace("[bold]", "").replace("[/bold]", "")
        clean_message = clean_message.replace("[green]", "").replace("[/green]", "")
        clean_message = clean_message.replace("[yellow]", "").replace("[/yellow]", "")
        clean_message = clean_message.replace("[red]", "").replace("[/red]", "")

        # 根据消息内容确定颜色
        color = "#4CAF50"
        if "错误" in message or "error" in message.lower():
            color = "#F44336"
        elif "警告" in message or "warning" in message.lower():
            color = "#FF9800"

        # 更新主窗口状态栏
        self.main_window.root.after(
            0,
            lambda: self.main_window.update_status(clean_message, color)
        )

    def run(self):
        """运行 GUI 主循环"""
        self.main_window.run()

    def quit(self):
        """退出"""
        self.main_window.quit()
