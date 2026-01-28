"""翻译模块"""

import re
from openai import OpenAI

from .config import TranslationConfig


class Translator:
    """翻译器"""

    def __init__(self, config: TranslationConfig):
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )

    def _remove_thinking_tags(self, text: str) -> str:
        """移除思考标签及其内容

        Args:
            text: 可能包含 <think>...</think> 标签的文本

        Returns:
            移除思考标签后的文本
        """
        # 移除 <think>...</think> 标签及其内容（支持多行）
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # 移除多余的空白
        cleaned = re.sub(r'\n\s*\n+', '\n', cleaned)
        return cleaned.strip()

    def translate(
        self, text: str, context: list[tuple[str, str]] | None = None
    ) -> str:
        """翻译文本

        Args:
            text: 要翻译的文本
            context: 历史上下文 [(original_text, translation), ...]

        Returns:
            翻译后的文本
        """
        if not text.strip():
            return ""

        try:
            # 构建消息列表
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"Translate from {self.config.source_lang} "
                        f"to {self.config.target_lang}. "
                        "Output translation only, no explanation."
                    ),
                }
            ]

            # 如果有上下文，添加到消息中
            if context:
                context_text = "Previous context:\n"
                for orig, trans in context:
                    if trans:  # 只包含已翻译的内容
                        context_text += f"{orig} -> {trans}\n"
                if len(context_text) > len("Previous context:\n"):
                    messages.append({"role": "system", "content": context_text})

            # 添加当前要翻译的文本
            messages.append({"role": "user", "content": text})

            # 准备 API 调用参数
            api_params = {
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }

            # 如果启用 thinking，添加 reasoning_effort 参数（DeepSeek R1）
            if self.config.thinking_level != "none":
                api_params["reasoning_effort"] = self.config.thinking_level

            response = self.client.chat.completions.create(**api_params)
            result = response.choices[0].message.content.strip()

            # 移除思考标签（如果有）
            result = self._remove_thinking_tags(result)

            return result
        except Exception as e:
            return f"[翻译错误: {e}]"
