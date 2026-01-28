"""音频捕获模块"""

import queue
from typing import Optional

import numpy as np
import sounddevice as sd

from .config import AudioConfig


class AudioCapture:
    """音频捕获器"""

    def __init__(self, config: AudioConfig):
        self.config = config
        self.audio_queue: queue.Queue = queue.Queue()
        self._stream: Optional[sd.InputStream] = None
        self.device_id: Optional[int] = None

    def find_device(self) -> int:
        """查找音频设备"""
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if (
                self.config.device_name in dev["name"]
                and dev["max_input_channels"] > 0
            ):
                self.device_id = i
                return i

        # 如果未找到，打印可用设备列表
        print("可用设备列表:")
        for i, dev in enumerate(devices):
            print(
                f"  [{i}] {dev['name']} "
                f"(in:{dev['max_input_channels']}, out:{dev['max_output_channels']})"
            )
        raise RuntimeError(f"未找到 {self.config.device_name}，请确认已安装并配置")

    def _audio_callback(self, indata, frames, time, status):
        """音频回调"""
        if status:
            print(f"音频状态: {status}")
        self.audio_queue.put(indata.copy())

    def start(self) -> sd.InputStream:
        """启动音频捕获"""
        if self.device_id is None:
            self.find_device()

        blocksize = int(self.config.sample_rate * self.config.blocksize_seconds)

        self._stream = sd.InputStream(
            device=self.device_id,
            channels=1,
            samplerate=self.config.sample_rate,
            dtype=np.float32,
            callback=self._audio_callback,
            blocksize=blocksize,
        )
        self._stream.start()
        return self._stream

    def stop(self):
        """停止音频捕获"""
        if self._stream:
            self._stream.stop()
            self._stream.close()

    def get_device_name(self) -> str:
        """获取设备名称"""
        if self.device_id is not None:
            return sd.query_devices(self.device_id)["name"]
        return "Unknown"
