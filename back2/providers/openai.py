import os
import time
import logging
from typing import Optional, Any

from back2.utils.api_keys import get_active_api_key
from .base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""

    # gpt-4o-mini / gpt-4.1-mini both ship 128k context. Stay well under it
    # so any token-count slop never trips a 400.
    context_window: int = 32_000

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        **kwargs
    ):
        super().__init__(model or "gpt-4o-mini")
        # Resolve the key in this order: explicit kwarg → env var →
        # ~/EasyForm/api_keys.json (written by the Electron API Keys modal).
        self.api_key = (
            api_key
            or os.getenv("OPENAI_API_KEY")
            or get_active_api_key("openai")
        )
        self._client = None
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def init_provider(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError("OpenAI library not installed") from e

        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set")

        self._client = OpenAI(api_key=self.api_key)
        logger.debug("OpenAI client initialized")

    def get_client(self):
        """Get OpenAI client, initializing if needed."""
        if self._client is None:
            self.init_provider()
        return self._client

    def query_gpt(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1
    ) -> str:
        """Query OpenAI API."""
        client = self.get_client()

        for attempt in range(self.max_retries):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                time.sleep(self.backoff_factor**attempt)
