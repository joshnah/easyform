from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    # Conservative cap to leave room for both prompt and reply on small
    # open-source models. Subclasses override to take advantage of larger
    # context windows (e.g. OpenAI gpt-4o-mini, Llama 3.1 70B at 128k).
    context_window: int = 4090

    def __init__(self, model: Optional[str] = None):
        self.model = model

    @abstractmethod
    def query_gpt(self, prompt: str, max_tokens: int, temperature: float) -> str:
        pass

    @abstractmethod
    def init_provider(self):
        pass

    @abstractmethod
    def get_client(self):
        pass


