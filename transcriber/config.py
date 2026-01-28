"""配置模块"""

from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path 

@dataclass
class AudioConfig:
    """音频配置（保留用于向后兼容，RealtimeSTT 内部管理音频）"""
    sample_rate: int = 16000
    blocksize_seconds: float = 0.2
    device_name: str = "BlackHole 2ch"


@dataclass
class TranscriptionConfig:
    """转录配置"""
    model_name: str = "tiny"
    device: str = "cpu"
    compute_type: str = "int8"
    source_lang: str = "en"


@dataclass
class ProcessingConfig:
    """处理配置"""
    translation_delay: float = 0.2  # 未完成句子的翻译延迟（秒）


@dataclass
class TranslationConfig:
    """翻译配置"""
    api_key: str = os.getenv("DEEPSEEK_API")
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    source_lang: str = "en"
    target_lang: str = "zh"
    temperature: float = 0.3
    max_tokens: int = 500
    thinking_level: str = "none"  # 思考模式等级: none, low, medium, high (DeepSeek R1/Ollama)


@dataclass
class DisplayConfig:
    """显示配置"""
    refresh_per_second: int = 4
    update_interval_ms: int = 250
    max_visible_items: int = 6  # GUI显示的最大句子数量
    translation_context_size: int = 10  # 传递给LLM的上下文句子数量


@dataclass
class StorageConfig:
    """存储配置"""
    storage_path: str = "~/.mac-transcriber"  # 数据存储路径


@dataclass
class OverlayConfig:
    """Overlay 窗口配置"""
    alpha: float = 0.8  # 透明度 (0.0-1.0)
    geometry: str = "800x300+100+100"  # 窗口大小和位置
    max_sentences: int = 4  # 最多显示句子数
    font_size_original: int = 16  # 原文字体大小
    font_size_translation: int = 14  # 翻译字体大小
    topmost: bool = True  # 是否置顶


class AppConfig:
    """应用统一配置管理器

    参考 LiveCaptions-Translator 的设计，支持：
    - JSON 持久化
    - 运行时动态修改
    - 配置变更回调
    """

    CONFIG_FILE = "config.json"

    def __init__(self):
        self.audio = AudioConfig()
        self.transcription = TranscriptionConfig()
        self.translation = TranslationConfig()
        self.processing = ProcessingConfig()
        self.display = DisplayConfig()
        self.storage = StorageConfig()
        self.overlay = OverlayConfig()

        # 配置变更回调
        self._callbacks = []

        # 加载配置
        self.load()

    def get_config_path(self) -> Path:
        """获取配置文件路径"""
        storage_path = Path(self.storage.storage_path).expanduser()
        storage_path.mkdir(parents=True, exist_ok=True)
        return storage_path / self.CONFIG_FILE

    def load(self) -> bool:
        """从 JSON 文件加载配置

        Returns:
            bool: 是否成功加载
        """
        config_path = self.get_config_path()

        if not config_path.exists():
            print(f"配置文件不存在，使用默认配置: {config_path}")
            return False

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 更新各个配置
            if 'audio' in data:
                self.audio = AudioConfig(**data['audio'])
            if 'transcription' in data:
                self.transcription = TranscriptionConfig(**data['transcription'])
            if 'translation' in data:
                # API key 从环境变量读取，不从配置文件读取
                translation_data = data['translation'].copy()
                if 'api_key' not in translation_data or not translation_data['api_key']:
                    translation_data['api_key'] = os.getenv("DEEPSEEK_API", "")
                self.translation = TranslationConfig(**translation_data)
            if 'processing' in data:
                self.processing = ProcessingConfig(**data['processing'])
            if 'display' in data:
                self.display = DisplayConfig(**data['display'])
            if 'storage' in data:
                self.storage = StorageConfig(**data['storage'])
            if 'overlay' in data:
                self.overlay = OverlayConfig(**data['overlay'])

            print(f"配置已加载: {config_path}")
            return True

        except Exception as e:
            print(f"加载配置失败: {e}")
            return False

    def save(self) -> bool:
        """保存配置到 JSON 文件

        Returns:
            bool: 是否成功保存
        """
        config_path = self.get_config_path()

        try:
            data = {
                'audio': asdict(self.audio),
                'transcription': asdict(self.transcription),
                'translation': asdict(self.translation),
                'processing': asdict(self.processing),
                'display': asdict(self.display),
                'storage': asdict(self.storage),
                'overlay': asdict(self.overlay),
            }

            # 不保存 API key 到文件（安全考虑）
            if 'api_key' in data['translation']:
                data['translation']['api_key'] = ""

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"配置已保存: {config_path}")
            return True

        except Exception as e:
            print(f"保存配置失败: {e}")
            return False

    def register_callback(self, callback):
        """注册配置变更回调

        Args:
            callback: 回调函数，签名为 callback(config_name, old_value, new_value)
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback):
        """取消注册配置变更回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_change(self, config_name: str, old_value, new_value):
        """通知配置变更"""
        for callback in self._callbacks:
            try:
                callback(config_name, old_value, new_value)
            except Exception as e:
                print(f"配置回调执行失败: {e}")

    def update_overlay_alpha(self, alpha: float):
        """更新 Overlay 透明度并保存"""
        old_value = self.overlay.alpha
        self.overlay.alpha = max(0.0, min(1.0, alpha))
        self._notify_change('overlay.alpha', old_value, self.overlay.alpha)
        self.save()

    def update_overlay_font_size(self, original_size: int = None, translation_size: int = None):
        """更新 Overlay 字体大小并保存"""
        if original_size is not None:
            old_value = self.overlay.font_size_original
            self.overlay.font_size_original = max(8, min(48, original_size))
            self._notify_change('overlay.font_size_original', old_value, self.overlay.font_size_original)

        if translation_size is not None:
            old_value = self.overlay.font_size_translation
            self.overlay.font_size_translation = max(8, min(48, translation_size))
            self._notify_change('overlay.font_size_translation', old_value, self.overlay.font_size_translation)

        self.save()

    def update_display_context_size(self, size: int):
        """更新上下文句子数并保存"""
        old_value = self.display.translation_context_size
        self.display.translation_context_size = max(0, min(50, size))
        self._notify_change('display.translation_context_size', old_value, self.display.translation_context_size)
        self.save()

    def update_overlay_max_sentences(self, count: int):
        """更新 Overlay 最大显示句子数并保存"""
        old_value = self.overlay.max_sentences
        self.overlay.max_sentences = max(1, min(10, count))
        self._notify_change('overlay.max_sentences', old_value, self.overlay.max_sentences)
        self.save()

    def update_translation_api(self, api_key: str = None, base_url: str = None, model: str = None, thinking_level: str = None):
        """更新翻译 API 配置并保存"""
        if api_key is not None:
            # API key 只在内存中，不保存到文件
            self.translation.api_key = api_key

        if base_url is not None:
            old_value = self.translation.base_url
            self.translation.base_url = base_url
            self._notify_change('translation.base_url', old_value, self.translation.base_url)

        if model is not None:
            old_value = self.translation.model
            self.translation.model = model
            self._notify_change('translation.model', old_value, self.translation.model)

        if thinking_level is not None:
            old_value = self.translation.thinking_level
            self.translation.thinking_level = thinking_level
            self._notify_change('translation.thinking_level', old_value, self.translation.thinking_level)

        self.save()
