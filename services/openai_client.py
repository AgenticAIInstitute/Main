from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


class OpenAIClient:
    def __init__(self) -> None:
        _load_env()
        self._api_key: Optional[str] = os.getenv("OPENAI_API_KEY", "").strip()
        raw_model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini").strip()
        self._model_name: str = raw_model
        self._client = None
        self._initialized: bool = False

        if self._api_key:
            self._init_client()

    def _init_client(self) -> None:
        try:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._api_key)
            self._initialized = True
            logger.info("OpenAI client initialized: model=%s", self._model_name)
        except Exception as e:
            logger.warning("OpenAI client init failed: %s", e)

    def is_available(self) -> bool:
        return bool(self._api_key) and self._initialized

    def generate(self, prompt: str) -> Optional[str]:
        if not self.is_available():
            return None
        try:
            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning("OpenAI generate failed: %s", e)
            return None


_openai_client: Optional[OpenAIClient] = None


def get_openai_client() -> OpenAIClient:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAIClient()
    return _openai_client
