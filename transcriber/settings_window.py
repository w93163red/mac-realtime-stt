"""设置窗口模块"""

import tkinter as tk
from tkinter import ttk, messagebox

from .config import AppConfig


class SettingsWindow:
    """设置窗口

    参考 LiveCaptions-Translator 的设计，提供：
    - 悬浮窗配置：透明度、字体大小、显示句子数、翻译上下文
    - 翻译配置：API key、base URL、model
    """

    def __init__(self, parent, config: AppConfig):
        """初始化设置窗口

        Args:
            parent: 父窗口
            config: 应用配置对象
        """
        self.parent = parent
        self.config = config

        # 创建顶层窗口
        self.window = tk.Toplevel(parent)
        self.window.title("⚙️ 设置")
        self.window.geometry("600x500")
        self.window.resizable(False, False)

        # 设置窗口居中
        self._center_window()

        # 设置模态（阻塞父窗口）
        self.window.transient(parent)
        self.window.grab_set()

        # 创建 UI
        self._setup_ui()

        # 窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_window(self):
        """居中窗口"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

    def _setup_ui(self):
        """设置 UI"""
        # 创建 Notebook（标签页）
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # 标签页 1: Overlay 设置（包含翻译上下文）
        overlay_frame = ttk.Frame(notebook, padding=20)
        notebook.add(overlay_frame, text="悬浮窗")
        self._setup_overlay_tab(overlay_frame)

        # 标签页 2: 翻译设置
        translation_frame = ttk.Frame(notebook, padding=20)
        notebook.add(translation_frame, text="翻译")
        self._setup_translation_tab(translation_frame)

        # 底部按钮栏
        button_frame = ttk.Frame(self.window, padding=10)
        button_frame.pack(fill="x", side="bottom")

        ttk.Button(
            button_frame,
            text="取消",
            command=self._on_close
        ).pack(side="right", padx=5)

        ttk.Button(
            button_frame,
            text="应用",
            command=self._on_apply
        ).pack(side="right", padx=5)

    def _setup_overlay_tab(self, parent):
        """设置 Overlay 标签页"""
        # 透明度设置
        row = 0
        ttk.Label(parent, text="透明度:").grid(row=row, column=0, sticky="w", pady=5)

        alpha_frame = ttk.Frame(parent)
        alpha_frame.grid(row=row, column=1, sticky="ew", pady=5)

        self.alpha_var = tk.DoubleVar(value=self.config.overlay.alpha)
        alpha_scale = ttk.Scale(
            alpha_frame,
            from_=0.1,
            to=1.0,
            variable=self.alpha_var,
            orient="horizontal",
            command=self._on_alpha_change
        )
        alpha_scale.pack(side="left", fill="x", expand=True)

        self.alpha_label = ttk.Label(alpha_frame, text=f"{self.config.overlay.alpha:.2f}")
        self.alpha_label.pack(side="left", padx=5)

        # 原文字体大小
        row += 1
        ttk.Label(parent, text="原文字体大小:").grid(row=row, column=0, sticky="w", pady=5)

        font_orig_frame = ttk.Frame(parent)
        font_orig_frame.grid(row=row, column=1, sticky="ew", pady=5)

        self.font_orig_var = tk.IntVar(value=self.config.overlay.font_size_original)
        font_orig_spinbox = ttk.Spinbox(
            font_orig_frame,
            from_=8,
            to=48,
            textvariable=self.font_orig_var,
            command=self._on_font_change,
            width=10
        )
        font_orig_spinbox.pack(side="left")

        ttk.Label(font_orig_frame, text="(8-48)").pack(side="left", padx=5)

        # 翻译字体大小
        row += 1
        ttk.Label(parent, text="翻译字体大小:").grid(row=row, column=0, sticky="w", pady=5)

        font_trans_frame = ttk.Frame(parent)
        font_trans_frame.grid(row=row, column=1, sticky="ew", pady=5)

        self.font_trans_var = tk.IntVar(value=self.config.overlay.font_size_translation)
        font_trans_spinbox = ttk.Spinbox(
            font_trans_frame,
            from_=8,
            to=48,
            textvariable=self.font_trans_var,
            command=self._on_font_change,
            width=10
        )
        font_trans_spinbox.pack(side="left")

        ttk.Label(font_trans_frame, text="(8-48)").pack(side="left", padx=5)

        # 最大显示句子数
        row += 1
        ttk.Label(parent, text="最大显示句子数:").grid(row=row, column=0, sticky="w", pady=5)

        max_sent_frame = ttk.Frame(parent)
        max_sent_frame.grid(row=row, column=1, sticky="ew", pady=5)

        self.max_sentences_var = tk.IntVar(value=self.config.overlay.max_sentences)
        max_sent_spinbox = ttk.Spinbox(
            max_sent_frame,
            from_=1,
            to=10,
            textvariable=self.max_sentences_var,
            command=self._on_max_sentences_change,
            width=10
        )
        max_sent_spinbox.pack(side="left")

        ttk.Label(max_sent_frame, text="(1-10)").pack(side="left", padx=5)

        # 翻译上下文句子数
        row += 1
        ttk.Label(parent, text="翻译上下文句子数:").grid(row=row, column=0, sticky="w", pady=5)

        context_frame = ttk.Frame(parent)
        context_frame.grid(row=row, column=1, sticky="ew", pady=5)

        self.context_size_var = tk.IntVar(value=self.config.display.translation_context_size)
        context_spinbox = ttk.Spinbox(
            context_frame,
            from_=0,
            to=50,
            textvariable=self.context_size_var,
            command=self._on_context_size_change,
            width=10
        )
        context_spinbox.pack(side="left")

        ttk.Label(context_frame, text="(0-50, 0=不使用上下文)").pack(side="left", padx=5)

        # 说明文本
        row += 1
        help_text = ttk.Label(
            parent,
            text="提示：增加上下文句子数可以提高翻译连贯性，\n但会增加 API 调用成本和延迟。",
            foreground="gray",
            justify="left"
        )
        help_text.grid(row=row, column=0, columnspan=2, sticky="w", pady=10)

        # 配置列宽
        parent.columnconfigure(1, weight=1)

    def _setup_translation_tab(self, parent):
        """设置翻译标签页"""
        # API Key
        row = 0
        ttk.Label(parent, text="API Key:").grid(row=row, column=0, sticky="w", pady=5)

        self.api_key_var = tk.StringVar(value=self.config.translation.api_key or "")
        api_key_entry = ttk.Entry(
            parent,
            textvariable=self.api_key_var,
            show="*"
        )
        api_key_entry.grid(row=row, column=1, sticky="ew", pady=5)

        # Base URL
        row += 1
        ttk.Label(parent, text="Base URL:").grid(row=row, column=0, sticky="w", pady=5)

        self.base_url_var = tk.StringVar(value=self.config.translation.base_url)
        base_url_entry = ttk.Entry(
            parent,
            textvariable=self.base_url_var
        )
        base_url_entry.grid(row=row, column=1, sticky="ew", pady=5)

        # Model
        row += 1
        ttk.Label(parent, text="Model:").grid(row=row, column=0, sticky="w", pady=5)

        self.model_var = tk.StringVar(value=self.config.translation.model)
        model_entry = ttk.Entry(
            parent,
            textvariable=self.model_var
        )
        model_entry.grid(row=row, column=1, sticky="ew", pady=5)

        # Thinking Level
        row += 1
        ttk.Label(parent, text="Thinking Level:").grid(row=row, column=0, sticky="w", pady=5)

        self.thinking_var = tk.StringVar(value=self.config.translation.thinking_level)
        thinking_combo = ttk.Combobox(
            parent,
            textvariable=self.thinking_var,
            values=["none", "low", "medium", "high"],
            state="readonly"
        )
        thinking_combo.grid(row=row, column=1, sticky="ew", pady=5)

        # 说明文本
        row += 1
        help_text = ttk.Label(
            parent,
            text="提示：修改 API 配置后，新的翻译请求将使用新配置。\n"
                 "API Key 不会保存到配置文件，仅在运行时有效。\n"
                 "Thinking Level 适用于 DeepSeek R1 等支持思考模式的模型。",
            foreground="gray",
            justify="left"
        )
        help_text.grid(row=row, column=0, columnspan=2, sticky="w", pady=10)

        # 配置列宽
        parent.columnconfigure(1, weight=1)

    def _on_alpha_change(self, value):
        """透明度变化"""
        alpha = float(value)
        self.alpha_label.config(text=f"{alpha:.2f}")
        self.config.update_overlay_alpha(alpha)

    def _on_font_change(self):
        """字体大小变化"""
        self.config.update_overlay_font_size(
            original_size=self.font_orig_var.get(),
            translation_size=self.font_trans_var.get()
        )

    def _on_max_sentences_change(self):
        """最大句子数变化"""
        self.config.update_overlay_max_sentences(self.max_sentences_var.get())

    def _on_context_size_change(self):
        """上下文大小变化"""
        self.config.update_display_context_size(self.context_size_var.get())

    def _on_apply(self):
        """应用所有设置"""
        # 验证必填字段
        base_url = self.base_url_var.get().strip()
        model = self.model_var.get().strip()

        if not base_url:
            messagebox.showwarning("警告", "Base URL 不能为空")
            return

        if not model:
            messagebox.showwarning("警告", "Model 不能为空")
            return

        # 获取 API Key（可以为空，用于 Ollama）
        api_key = self.api_key_var.get().strip()

        # 获取 Thinking Level
        thinking_level = self.thinking_var.get()

        # 统一更新所有翻译 API 配置
        self.config.update_translation_api(
            api_key=api_key if api_key else None,
            base_url=base_url,
            model=model,
            thinking_level=thinking_level
        )

        messagebox.showinfo("成功", "所有设置已保存\n\nAPI Key 仅在运行时有效，不会保存到配置文件。")
        self.window.destroy()

    def _on_close(self):
        """取消并关闭窗口"""
        self.window.destroy()

    def show(self):
        """显示设置窗口（阻塞）"""
        self.window.wait_window()
