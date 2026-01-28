"""主窗口模块 - 完整历史记录显示"""

import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from .data_manager import DataManager, SentenceRecord


class MainWindow:
    """主应用窗口

    特性:
    - 显示完整对话历史
    - 支持滚动查看
    - 显示时间戳
    - 分会话管理
    - 导出功能
    """

    def __init__(self, data_manager: DataManager):
        self.root = tk.Tk()
        self.data_manager = data_manager
        self.overlay_window = None  # 后续设置

        self._setup_window()
        self._setup_ui()

    def _setup_window(self):
        """窗口配置"""
        self.root.title("🎤 实时字幕 + 翻译 - 完整记录")
        self.root.geometry("900x700")
        self.root.configure(bg="#f5f5f5")

        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_ui(self):
        """设置 UI"""
        # 顶部工具栏
        self._setup_toolbar()

        # 中间历史记录显示区
        self._setup_history_view()

        # 底部状态栏
        self._setup_statusbar()

    def _setup_toolbar(self):
        """工具栏: 清空、导出、设置等"""
        toolbar = ttk.Frame(self.root, padding=10)
        toolbar.pack(fill="x", side="top")

        # 会话信息
        session_id = self.data_manager.get_current_session_id()
        self.session_label = ttk.Label(
            toolbar,
            text=f"当前会话: {session_id}",
            font=("Arial", 10)
        )
        self.session_label.pack(side="left", padx=5)

        # 按钮
        ttk.Button(
            toolbar,
            text="新建会话",
            command=self._new_session
        ).pack(side="left", padx=5)

        ttk.Button(
            toolbar,
            text="导出 JSON",
            command=self._export_json
        ).pack(side="left", padx=5)

        ttk.Button(
            toolbar,
            text="导出 TXT",
            command=self._export_txt
        ).pack(side="left", padx=5)

        ttk.Button(
            toolbar,
            text="清空历史",
            command=self._clear_history
        ).pack(side="left", padx=5)

        ttk.Button(
            toolbar,
            text="显示/隐藏悬浮窗",
            command=self._toggle_overlay
        ).pack(side="right", padx=5)

    def _setup_history_view(self):
        """历史记录显示区"""
        frame = ttk.Frame(self.root)
        frame.pack(fill="both", expand=True, padx=15, pady=10)

        # 使用 Text widget + Scrollbar
        self.history_text = tk.Text(
            frame,
            wrap="word",
            font=("Arial", 11),
            bg="white",
            fg="#333333",
            relief="solid",
            borderwidth=1,
            padx=15,
            pady=15,
            state="disabled",
        )

        scrollbar = ttk.Scrollbar(frame, command=self.history_text.yview)
        self.history_text.configure(yscrollcommand=scrollbar.set)

        self.history_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 配置标签样式
        self.history_text.tag_configure("timestamp",
            foreground="#999999",
            font=("Arial", 9))
        self.history_text.tag_configure("original",
            foreground="#2196F3",
            font=("Arial", 12, "bold"))
        self.history_text.tag_configure("translation",
            foreground="#4CAF50",
            font=("Arial", 11))
        self.history_text.tag_configure("separator",
            foreground="#EEEEEE")
        self.history_text.tag_configure("loading",
            foreground="#999999",
            font=("Arial", 10, "italic"))

        # 支持鼠标滚轮
        self.history_text.bind("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        """处理鼠标滚轮"""
        self.history_text.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _setup_statusbar(self):
        """状态栏"""
        statusbar = ttk.Frame(self.root, padding=5)
        statusbar.pack(fill="x", side="bottom")

        self.status_label = ttk.Label(
            statusbar,
            text="🟢 正在监听...",
            font=("Arial", 9),
        )
        self.status_label.pack(side="left")

        self.count_label = ttk.Label(
            statusbar,
            text="总句数: 0",
            font=("Arial", 9),
        )
        self.count_label.pack(side="right")

    def set_overlay_window(self, overlay_window):
        """设置 Overlay 窗口的引用

        Args:
            overlay_window: OverlayWindow 实例
        """
        self.overlay_window = overlay_window

    def update_history(self, all_sentences: list[SentenceRecord]):
        """更新完整历史记录显示

        Args:
            all_sentences: 所有句子列表
        """
        self.history_text.configure(state="normal")
        self.history_text.delete("1.0", "end")

        if not all_sentences:
            self.history_text.insert("end", "暂无记录\n\n", "loading")
            self.history_text.insert("end", "请开始说话，系统会自动记录并翻译...", "loading")
        else:
            for i, sentence in enumerate(all_sentences):
                # 时间戳
                time_str = self._format_timestamp(sentence.timestamp)
                self.history_text.insert("end", f"[{time_str}] ", "timestamp")

                # 原文
                self.history_text.insert("end", sentence.original, "original")
                self.history_text.insert("end", "\n")

                # 翻译
                if sentence.translation:
                    self.history_text.insert("end", sentence.translation, "translation")
                else:
                    self.history_text.insert("end", "⏳ 翻译中...", "loading")

                # 分隔线
                if i < len(all_sentences) - 1:
                    self.history_text.insert("end", "\n" + "─" * 80 + "\n", "separator")
                else:
                    self.history_text.insert("end", "\n")

        self.history_text.configure(state="disabled")
        self.history_text.see("end")

        # 更新计数
        self.count_label.config(text=f"总句数: {len(all_sentences)}")

    def update_status(self, status: str, color: str = "#4CAF50"):
        """更新状态栏

        Args:
            status: 状态文本
            color: 颜色
        """
        self.status_label.config(text=status, foreground=color)

    def _format_timestamp(self, timestamp: float) -> str:
        """格式化时间戳

        Args:
            timestamp: Unix timestamp

        Returns:
            str: 格式化的时间字符串
        """
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%H:%M:%S")

    def _new_session(self):
        """新建会话"""
        result = messagebox.askyesno(
            "新建会话",
            "确定要开始新会话吗？当前会话将被保存。"
        )
        if result:
            self.data_manager.new_session()
            session_id = self.data_manager.get_current_session_id()
            self.session_label.config(text=f"当前会话: {session_id}")
            self.update_history([])
            messagebox.showinfo("成功", f"已创建新会话: {session_id}")

    def _export_json(self):
        """导出为 JSON"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            try:
                self.data_manager.export_to_json(filepath)
                messagebox.showinfo("成功", f"已导出到: {filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")

    def _export_txt(self):
        """导出为 TXT"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filepath:
            try:
                self.data_manager.export_to_txt(filepath)
                messagebox.showinfo("成功", f"已导出到: {filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")

    def _clear_history(self):
        """清空历史"""
        result = messagebox.askyesno(
            "清空历史",
            "确定要清空当前会话的所有记录吗？此操作不可恢复！"
        )
        if result:
            self.data_manager.clear_current_session()
            self.update_history([])
            messagebox.showinfo("成功", "已清空当前会话记录")

    def _toggle_overlay(self):
        """切换悬浮窗显示/隐藏"""
        if self.overlay_window:
            self.overlay_window.toggle()

    def _on_close(self):
        """窗口关闭事件"""
        result = messagebox.askyesno(
            "退出",
            "确定要退出应用吗？"
        )
        if result:
            self.data_manager.stop()
            self.root.quit()
            self.root.destroy()

    def run(self):
        """运行 GUI 主循环"""
        self.root.mainloop()

    def quit(self):
        """退出"""
        self.data_manager.stop()
        self.root.quit()
        self.root.destroy()
