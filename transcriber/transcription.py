"""转录模块"""

from typing import Generator, Tuple

import numpy as np
from faster_whisper import WhisperModel
from faster_whisper.transcribe import Segment, TranscriptionInfo

from .config import TranscriptionConfig


class Transcriber:
    """转录器"""

    def __init__(self, config: TranscriptionConfig):
        self.config = config
        self.model: WhisperModel = self._load_model()

    def _load_model(self) -> WhisperModel:
        """加载 Whisper 模型"""
        return WhisperModel(
            self.config.model_name,
            device=self.config.device,
            compute_type=self.config.compute_type,
        )

    def transcribe(
        self, audio: np.ndarray
    ) -> Tuple[Generator[Segment, None, None], TranscriptionInfo]:
        """转录音频"""
        segments, info = self.model.transcribe(
            audio,
            language=self.config.source_lang,
            vad_filter=True,
            vad_parameters={
                "min_silence_duration_ms": self.config.min_silence_duration_ms,
                "threshold": self.config.vad_threshold,
                "min_speech_duration_ms": int(
                    self.config.min_speech_duration * 1000
                ),
            },
        )
        return segments, info

    @staticmethod
    def segments_to_text(segments: Generator[Segment, None, None]) -> str:
        """将语音段转换为文本"""
        return " ".join(seg.text for seg in segments).strip()
