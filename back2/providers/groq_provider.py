from typing import Optional, Any
import os
import time
import logging

from .base import LLMProvider

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.1-8b-instant"
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 2.0
DEFAULT_MIN_INTERVAL = 2.0  # seconds between requests (simple rate limit)


class GroqProvider(LLMProvider):
    """Groq provider with simple per-instance rate limiting and retry."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        min_interval: float = DEFAULT_MIN_INTERVAL,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        **kwargs: Any,
    ):
        super().__init__(model)
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self._client = None
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.min_interval = min_interval
        self._last_request_time = 0.0
        self.max_retries = int(max_retries)
        self.backoff_factor = float(backoff_factor)
        if model:
            self.model = model
        else:
            self.model = self.model or DEFAULT_MODEL

    def init_provider(self):
        """Initialize Groq client."""
        try:
            from groq import Groq
        except ImportError as e:
            raise RuntimeError("Groq library not installed") from e

        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY not set")

        self._client = Groq(api_key=self.api_key)
        logger.debug("Groq client initialized")

    def get_client(self):
        """Get Groq client, initializing if needed."""
        if self._client is None:
            self.init_provider()
        return self._client

    def query_gpt(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1
    ) -> str:
        """Query Groq API with rate limiting."""
        client = self.get_client()

        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            logger.debug("Rate limiting: sleeping for %.2f seconds", sleep_time)
            time.sleep(sleep_time)

        for attempt in range(self.max_retries):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                self._last_request_time = time.time()
                return response.choices[0].message.content.strip()
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                sleep_time = self.backoff_factor**attempt
                logger.warning(
                    "Groq request failed (attempt %d), retrying in %.1fs: %s",
                    attempt + 1,
                    sleep_time,
                    e,
                )
                time.sleep(sleep_time)
