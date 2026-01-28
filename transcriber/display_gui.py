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
