from abc import ABC, abstractmethod
from typing import Optional

class LLMProvider(ABC):
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


