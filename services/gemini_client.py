from __future__ import annotations
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


class GeminiClient:
    def __init__(self) -> None:
        _load_env()
        self._api_key: Optional[str] = os.getenv("GEMINI_API_KEY", "").strip()
        raw_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
        # API는 "models/xxx" 또는 "xxx" 둘 다 허용하지만 내부적으로 통일
        self._model_name: str = raw_model if raw_model.startswith("models/") else f"models/{raw_model}"
        self._client = None
        self._initialized: bool = False

        if self._api_key:
            self._init_client()

    def _init_client(self) -> None:
        try:
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
            self._initialized = True
            logger.info("Gemini client initialized: model=%s", self._model_name)
        except ImportError:
            # 구 패키지로 fallback
            try:
                import google.generativeai as genai_old  # type: ignore
                genai_old.configure(api_key=self._api_key)
                self._client = genai_old.GenerativeModel(self._model_name)
                self._initialized = True
                self._legacy = True
                logger.info("Gemini legacy client initialized: model=%s", self._model_name)
            except Exception as e:
                logger.warning("Gemini client init failed: %s", e)
        except Exception as e:
            logger.warning("Gemini client init failed: %s", e)

    def is_available(self) -> bool:
        return bool(self._api_key) and self._initialized

    def generate(self, prompt: str) -> Optional[str]:
        if not self.is_available():
            return None
        try:
            from google import genai
            response = self._client.models.generate_content(
                model=self._model_name, contents=prompt
            )
            return response.text.strip()
        except ImportError:
            pass
        except Exception as e:
            logger.warning("Gemini generate failed: %s", e)
            return None

        # legacy fallback
        try:
            response = self._client.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.warning("Gemini generate failed (legacy): %s", e)
            return None


_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
