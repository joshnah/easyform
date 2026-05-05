"""
Provider registry and factory for LLM providers.
Easy to extend: just add new provider classes and register them.
"""

from typing import Dict, Type, Literal, get_args
from back2.providers.base import LLMProvider
from back2.providers.openai_provider import OpenAIProvider
from back2.providers.groq_provider import GroqProvider
from back2.providers.local_provider import LocalProvider
from back2.providers.anythingllm_provider import AnythingLLMProvider

# Registry mapping provider names to classes
PROVIDER_REGISTRY: Dict[str, Type[LLMProvider]] = {
    "openai": OpenAIProvider,
    "groq": GroqProvider,
    "local": LocalProvider,
    "anythingllm": AnythingLLMProvider,
}

# Type-safe provider names for FastAPI/Pydantic
ProviderType = Literal["openai", "groq", "local", "anythingllm"]


def get_available_providers() -> list[str]:
    """Get list of available provider names."""
    return list(PROVIDER_REGISTRY.keys())


def get_provider(provider_name: str, **kwargs) -> LLMProvider:
    """
    Factory function to create provider instances.

    Args:
        provider_name: Name of the provider ("openai", "groq", etc.)
        **kwargs: Provider-specific configuration

    Returns:
        Configured provider instance

    Raises:
        ValueError: If provider name is not supported
    """
    if provider_name not in PROVIDER_REGISTRY:
        available = ", ".join(get_available_providers())
        raise ValueError(
            f"Unsupported provider '{provider_name}'. Available: {available}"
        )

    provider_class = PROVIDER_REGISTRY[provider_name]
    return provider_class(**kwargs)


def register_provider(name: str, provider_class: Type[LLMProvider]):
    """
    Register a new provider (for easy extension).

    Args:
        name: Provider name
        provider_class: Provider class inheriting from LLMProvider
    """
    PROVIDER_REGISTRY[name] = provider_class


__all__ = [
    "LLMProvider",
    "ProviderType",
    "get_provider",
    "get_available_providers",
    "register_provider",
    "OpenAIProvider",
    "GroqProvider",
    "LocalProvider",
    "AnythingLLMProvider",
]
