"""
Provider registry and factory for LLM providers.
Easy to extend: just add new provider classes and register them.
"""

from typing import Dict, Literal, Type

from back2.providers.anythingllm import AnythingLLMProvider
from back2.providers.base import LLMProvider
from back2.providers.groq import GroqProvider
from back2.providers.local import LocalProvider
from back2.providers.openai import OpenAIProvider

# Registry mapping provider names to classes
PROVIDER_REGISTRY: Dict[str, Type[LLMProvider]] = {
    "openai": OpenAIProvider,
    "groq": GroqProvider,
    "local": LocalProvider,
    "anythingllm": AnythingLLMProvider,
}

# Type-safe provider names for FastAPI/Pydantic
ProviderType = Literal["openai", "groq", "local", "anythingllm"]

# Cache instances by name for the no-kwargs case (the hot path used by API
# routes). Each request through `/document/analyze` and `/context/search`
# previously rebuilt the SDK client; now they share one per provider.
_PROVIDER_CACHE: Dict[str, LLMProvider] = {}


def get_available_providers() -> list[str]:
    """Get list of available provider names."""
    return list(PROVIDER_REGISTRY.keys())


def get_provider(provider_name: str, **kwargs) -> LLMProvider:
    """
    Factory function to create provider instances.

    No-kwargs calls share a process-wide cached instance per provider name
    (so SDK clients, rate-limit state, and credentials are reused across
    requests). Pass kwargs explicitly to bypass the cache.

    Args:
        provider_name: Name of the provider ("openai", "groq", etc.)
        **kwargs: Provider-specific configuration

    Raises:
        ValueError: If provider name is not supported
    """
    if provider_name not in PROVIDER_REGISTRY:
        available = ", ".join(get_available_providers())
        raise ValueError(
            f"Unsupported provider '{provider_name}'. Available: {available}"
        )

    if not kwargs and provider_name in _PROVIDER_CACHE:
        return _PROVIDER_CACHE[provider_name]

    provider_class = PROVIDER_REGISTRY[provider_name]
    instance = provider_class(**kwargs)
    if not kwargs:
        _PROVIDER_CACHE[provider_name] = instance
    return instance


def clear_provider_cache() -> None:
    """Drop cached provider instances (useful in tests / after key rotation)."""
    _PROVIDER_CACHE.clear()


def register_provider(name: str, provider_class: Type[LLMProvider]):
    """
    Register a new provider (for easy extension).

    Args:
        name: Provider name
        provider_class: Provider class inheriting from LLMProvider
    """
    PROVIDER_REGISTRY[name] = provider_class
    _PROVIDER_CACHE.pop(name, None)


__all__ = [
    "LLMProvider",
    "ProviderType",
    "get_provider",
    "get_available_providers",
    "register_provider",
    "clear_provider_cache",
    "OpenAIProvider",
    "GroqProvider",
    "LocalProvider",
    "AnythingLLMProvider",
]
