"""Overlay 窗口模块 - 半透明字幕悬浮窗"""

import tkinter as tk
from tkinter import ttk

from .config import AppConfig
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

    def __init__(self, root: tk.Tk, data_manager: DataManager, config: AppConfig = None):
        self.root = root
        self.data_manager = data_manager
        self.config = config  # 配置对象
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

        # 注册配置变更回调
        if self.config:
            self.config.register_callback(self._on_config_change)

    def _setup_window(self):
        """窗口基础配置"""
        # 使用配置中的几何信息和透明度
        geometry = self.config.overlay.geometry if self.config else "800x300+100+100"
        alpha = self.config.overlay.alpha if self.config else 0.8
        topmost = self.config.overlay.topmost if self.config else True

        # 标题和大小
        self.window.title("字幕悬浮窗")
        self.window.geometry(geometry)

        # 半透明黑色背景
        self.window.configure(bg="#000000")
        self.window.attributes('-alpha', alpha)

        # 窗口置顶
        self.window.attributes('-topmost', topmost)

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

        # 配置标签样式（使用配置中的字体大小）
        font_size_original = self.config.overlay.font_size_original if self.config else 16
        font_size_translation = self.config.overlay.font_size_translation if self.config else 14

        self.text_widget.tag_configure("original",
            foreground="#FFFFFF",
            font=("Arial", font_size_original, "bold"))
        self.text_widget.tag_configure("translation",
            foreground="#00FF00",
            font=("Arial", font_size_translation, "normal"))
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

    def update_with_realtime(self, completed_sentences: list[SentenceRecord], realtime_text: str, realtime_translation: str = ""):
        """更新显示：已完成的句子 + 实时文本 + 实时翻译

        Args:
            completed_sentences: 已完成的句子列表（最多 3 句）
            realtime_text: 当前正在转录的实时文本
            realtime_translation: 实时文本的翻译（可选）
        """
        # 检查窗口是否仍然存在
        try:
            if not self.window.winfo_exists():
                return
        except Exception:
            return

        self.text_widget.configure(state="normal")
        self.text_widget.delete("1.0", "end")

        # 如果既没有完成的句子也没有实时文本，显示等待提示
        if not completed_sentences and not realtime_text:
            self.text_widget.insert("end", "等待语音输入...", "loading")
        else:
            # 合并已完成句子的原文
            completed_originals = [s.original for s in completed_sentences]

            # 添加实时文本到原文列表
            all_originals = completed_originals.copy()
            if realtime_text and realtime_text.strip():
                all_originals.append(realtime_text)

            # 显示原文段落（已完成 + 实时）
            if all_originals:
                original_paragraph = " ".join(all_originals)
                self.text_widget.insert("end", original_paragraph, "original")
                self.text_widget.insert("end", "\n\n")

            # 显示翻译段落（已完成句子的翻译 + 实时翻译）
            translations = []
            for sentence in completed_sentences:
                if sentence.translation and sentence.translation.strip():
                    translations.append(sentence.translation)

            # 添加实时翻译
            if realtime_translation and realtime_translation.strip():
                translations.append(realtime_translation)

            if translations:
                translation_paragraph = " ".join(translations)
                self.text_widget.insert("end", translation_paragraph, "translation")

        self.text_widget.configure(state="disabled")

        # 自动滚动到底部
        self.text_widget.see("end")

    def update_realtime_text(self, text: str):
        """更新实时文本（用于显示正在转录的内容，不访问数据库）

        已废弃：请使用 update_with_realtime() 方法
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

    def _on_config_change(self, config_name: str, old_value, new_value):
        """配置变更回调 - 实时更新窗口设置

        Args:
            config_name: 配置名称（如 'overlay.alpha'）
            old_value: 旧值
            new_value: 新值
        """
        try:
            if not self.window.winfo_exists():
                return
        except Exception:
            return

        if config_name == 'overlay.alpha':
            self.window.attributes('-alpha', new_value)
        elif config_name == 'overlay.font_size_original':
            self.text_widget.tag_configure("original",
                foreground="#FFFFFF",
                font=("Arial", new_value, "bold"))
        elif config_name == 'overlay.font_size_translation':
            self.text_widget.tag_configure("translation",
                foreground="#00FF00",
                font=("Arial", new_value, "normal"))
        elif config_name == 'overlay.topmost':
            self.window.attributes('-topmost', new_value)

    def destroy(self):
        """销毁窗口"""
        # 取消注册回调
        if self.config:
            self.config.unregister_callback(self._on_config_change)
        self.window.destroy()
