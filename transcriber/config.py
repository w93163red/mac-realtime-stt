"""配置模块"""

from dataclasses import dataclass
import os 

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
    default_alpha: float = 0.6  # 默认透明度 (0.0-1.0)
    default_geometry: str = "800x300+100+100"  # 默认窗口大小和位置
    max_sentences: int = 4  # 最多显示句子数
