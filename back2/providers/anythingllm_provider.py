import os
import time
import uuid
import requests
import logging
import yaml
from typing import Optional

from back2.paths import resource_path
from .base import LLMProvider

logger = logging.getLogger(__name__)


class AnythingLLMProvider(LLMProvider):
    """AnythingLLM provider implementation."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        workspace_slug: Optional[str] = None,
        config_path: Optional[str] = None,
        timeout: int = 200,
        max_retries: int = 3,
        **kwargs,
    ):
        super().__init__(model or "default")
        self.api_key = api_key
        self.base_url = base_url
        self.workspace_slug = workspace_slug
        self.config_path = config_path or str(resource_path("config.yaml"))
        self.timeout = timeout
        self.max_retries = max_retries
        self._headers = None
        self._chat_url = None

    def init_provider(self):
        """Initialize AnythingLLM client from config."""
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            raise RuntimeError(f"Config file not found: {self.config_path}")

        api_key = self.api_key or config.get("api_key")
        base_url = self.base_url or config.get("model_server_base_url")
        workspace_slug = self.workspace_slug or config.get("workspace_slug")

        if not api_key:
            raise RuntimeError("AnythingLLM API key not found")
        if not base_url:
            raise RuntimeError("AnythingLLM base URL not found")
        if not workspace_slug:
            raise RuntimeError("AnythingLLM workspace slug not found")

        self._chat_url = f"{base_url}/workspace/{workspace_slug}/chat"
        self._headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        logger.debug("AnythingLLM client initialized")

    def get_client(self):
        """Ensure provider is initialized."""
        if self._headers is None or self._chat_url is None:
            self.init_provider()
        return True

    def query_gpt(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1
    ) -> str:
        """Query AnythingLLM API."""
        self.get_client()

        data = {
            "message": prompt,
            "mode": "chat",
            "sessionId": str(uuid.uuid4()),
            "attachments": [],
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self._chat_url,
                    headers=self._headers,
                    json=data,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                result = response.json()
                return result.get("textResponse", "").strip()
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                time.sleep(2**attempt)
