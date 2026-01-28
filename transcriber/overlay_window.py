"""Overlay 窗口模块 - 半透明字幕悬浮窗"""

import tkinter as tk
from tkinter import ttk

from .data_manager import DataManager, SentenceRecord


class OverlayWindow:
    """半透明字幕悬浮窗

    特性:
    - 使用 tk.Toplevel 创建
    - 半透明黑色背景（alpha=0.85）
    - 窗口置顶
    - 可拖动
    - 可调整大小
    - 显示最近 3-4 句话（原文+翻译）
    """

    def __init__(self, root: tk.Tk, data_manager: DataManager):
        self.root = root
        self.data_manager = data_manager
        self.window = tk.Toplevel(root)

        # 拖动和调整大小的状态
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._resize_start_x = 0
        self._resize_start_y = 0
        self._resize_start_width = 0
        self._resize_start_height = 0

        self._setup_window()
        self._setup_ui()
        self._setup_drag_resize()

    def _setup_window(self):
        """窗口基础配置"""
        # 标题和大小
        self.window.title("字幕悬浮窗")
        self.window.geometry("800x300+100+100")

        # 半透明黑色背景
        self.window.configure(bg="#000000")
        self.window.attributes('-alpha', 0.85)

        # 窗口置顶
        self.window.attributes('-topmost', True)

        # macOS 特定配置（如果需要）
        try:
            self.window.attributes('-transparent', True)
        except tk.TclError:
            pass  # 某些平台不支持

    def _setup_ui(self):
        """设置 UI 布局"""
        # 创建主框架
        main_frame = tk.Frame(self.window, bg="#000000")
        main_frame.pack(fill="both", expand=True)

        # 使用 Text widget 显示字幕
        self.text_widget = tk.Text(
            main_frame,
            wrap="word",
            font=("Arial", 16, "bold"),
            bg="#000000",
            fg="#FFFFFF",
            relief="flat",
            padx=20,
            pady=20,
            state="disabled",
            borderwidth=0,
            highlightthickness=0,
        )
        self.text_widget.pack(fill="both", expand=True)

        # 配置标签样式
        self.text_widget.tag_configure("original",
            foreground="#FFFFFF",
            font=("Arial", 16, "bold"))
        self.text_widget.tag_configure("translation",
            foreground="#00FF00",
            font=("Arial", 14, "normal"))
        self.text_widget.tag_configure("loading",
            foreground="#888888",
            font=("Arial", 12, "italic"))

        # 右下角调整大小的把手
        resize_handle = tk.Label(
            main_frame,
            text="⋰",
            font=("Arial", 20),
            bg="#333333",
            fg="#FFFFFF",
            cursor="sizing",  # macOS 兼容的光标
            width=2,
            height=1
        )
        resize_handle.place(relx=1.0, rely=1.0, anchor="se", x=-5, y=-5)

        # 绑定 resize handle 的事件
        resize_handle.bind("<ButtonPress-1>", self._start_resize)
        resize_handle.bind("<B1-Motion>", self._on_resize)

    def _setup_drag_resize(self):
        """设置拖动功能"""
        # 拖动窗口（绑定到整个窗口）
        self.window.bind("<ButtonPress-1>", self._start_drag)
        self.window.bind("<B1-Motion>", self._on_drag)

        # 鼠标进入时增加不透明度
        self.window.bind("<Enter>", lambda e: self.window.attributes('-alpha', 0.95))
        # 鼠标离开时恢复透明度
        self.window.bind("<Leave>", lambda e: self.window.attributes('-alpha', 0.85))

    def _start_drag(self, event):
        """开始拖动"""
        # 忽略 resize handle 上的点击
        if event.widget != self.window and event.widget != self.text_widget:
            return

        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag(self, event):
        """拖动窗口"""
        # 忽略 resize handle 上的拖动
        if event.widget != self.window and event.widget != self.text_widget:
            return

        x = self.window.winfo_x() + event.x - self._drag_start_x
        y = self.window.winfo_y() + event.y - self._drag_start_y
        self.window.geometry(f"+{x}+{y}")

    def _start_resize(self, event):
        """开始调整大小"""
        self._resize_start_x = event.x_root
        self._resize_start_y = event.y_root
        self._resize_start_width = self.window.winfo_width()
        self._resize_start_height = self.window.winfo_height()

    def _on_resize(self, event):
        """调整窗口大小"""
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y

        new_width = max(400, self._resize_start_width + dx)
        new_height = max(150, self._resize_start_height + dy)

        self.window.geometry(f"{new_width}x{new_height}")

    def update_realtime_text(self, text: str):
        """更新实时文本（用于显示正在转录的内容，不访问数据库）

        Args:
            text: 实时文本
        """
        # 检查窗口是否仍然存在
        try:
            if not self.window.winfo_exists():
                return
        except Exception:
            return

        self.text_widget.configure(state="normal")
        self.text_widget.delete("1.0", "end")

        if text and text.strip():
            # 显示实时文本（白色）
            self.text_widget.insert("end", text, "original")
        else:
            # 没有内容时显示等待提示
            self.text_widget.insert("end", "等待语音输入...", "loading")

        self.text_widget.configure(state="disabled")

        # 自动滚动到底部
        self.text_widget.see("end")

    def update_display(self, sentences: list[SentenceRecord]):
        """更新显示内容（段落模式：原文和翻译都显示为段落）

        Args:
            sentences: 最近的句子列表（已按时间排序）
        """
        # 检查窗口是否仍然存在
        try:
            if not self.window.winfo_exists():
                return
        except Exception:
            return

        self.text_widget.configure(state="normal")
        self.text_widget.delete("1.0", "end")

        # 只显示最后 4 句
        display_sentences = sentences[-4:] if len(sentences) > 4 else sentences

        if not display_sentences:
            # 没有内容时显示等待提示
            self.text_widget.insert("end", "等待语音输入...", "loading")
        else:
            # 合并所有原文成一个段落
            originals = [s.original for s in display_sentences]
            original_paragraph = " ".join(originals)

            # 显示原文段落
            self.text_widget.insert("end", original_paragraph, "original")
            self.text_widget.insert("end", "\n\n")

            # 收集所有有翻译的句子的翻译，合并成段落
            translations = []
            for sentence in display_sentences:
                if sentence.translation and sentence.translation.strip():
                    translations.append(sentence.translation)

            # 显示翻译段落（合并所有翻译）
            if translations:
                translation_paragraph = " ".join(translations)
                self.text_widget.insert("end", translation_paragraph, "translation")

        self.text_widget.configure(state="disabled")

        # 自动滚动到底部
        self.text_widget.see("end")

    def show(self):
        """显示窗口"""
        self.window.deiconify()

    def hide(self):
        """隐藏窗口"""
        self.window.withdraw()

    def toggle(self):
        """切换显示/隐藏"""
        if self.window.state() == "withdrawn":
            self.show()
        else:
            self.hide()

    def destroy(self):
        """销毁窗口"""
        self.window.destroy()
