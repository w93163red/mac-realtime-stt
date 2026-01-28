"""翻译模块"""

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

            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[翻译错误: {e}]"
