import os
import logging
from typing import Optional, Literal
import time


import asyncio
import httpx
import json
import requests
import sys
import threading
import time
import yaml
from dotenv import load_dotenv

load_dotenv()

# Try to import both clients
try:
    from openai import OpenAI
    import openai as _openai_module

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI package not available")

try:
    from groq import Groq

    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logging.warning("Groq package not available")

_openai_client = None
_groq_client = None
_max_retries = 5  # Increased retries for rate limits
_backoff_factor = 2.0

# Rate limiting configuration - can be adjusted for free tier users
GROQ_FREE_TIER_MODE = True  # Set to True for more aggressive rate limiting

_last_groq_request_time = 0
_groq_min_interval = (
    2.0 if GROQ_FREE_TIER_MODE else 0.2
)  # 2 seconds for free tier, 0.2 second for paid

# Default provider and model configurations
DEFAULT_PROVIDER = "openai"  # Changed default to groq
DEFAULT_MODELS = {
    "openai": "gpt-4.5-preview",
    "groq": "meta-llama/llama-4-scout-17b-16e-instruct",
}


def init_openai() -> Optional[OpenAI]:
    """Initialize OpenAI API client using the OPENAI_API_KEY environment variable."""
    if not OPENAI_AVAILABLE:
        logging.error("OpenAI package not installed")
        return None

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.warning("OPENAI_API_KEY environment variable not set.")
        return None

    try:
        client = OpenAI(api_key=api_key)
        return client
    except Exception as e:
        logging.error(f"Failed to initialize OpenAI client: {e}")
        return None


def init_groq() -> Optional[Groq]:
    """Initialize Groq API client using the GROQ_API_KEY environment variable."""
    if not GROQ_AVAILABLE:
        logging.error("Groq package not installed")
        return None

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logging.warning("GROQ_API_KEY environment variable not set.")
        return None

    try:
        client = Groq(api_key=api_key)
        return client
    except Exception as e:
        logging.error(f"Failed to initialize Groq client: {e}")
        return None


def init_anythingllm():
    """Initialize the AnythingLLM client using the ANYTHINGLLM_API_KEY environment variable."""
    try:
        with open("config.yaml", "r") as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        raise FileNotFoundError(
            "config.yaml not found. Please create a config file with your API key and base URL."
        )

    api_key = config["api_key"]
    if not api_key:
        raise ValueError("Anything LLM API key not found in config.yaml.")

    base_url = config["model_server_base_url"]
    if not base_url:
        raise ValueError("Base URL not found in config.yaml.")

    workspace_slug = config["workspace_slug"]
    if not workspace_slug:
        raise ValueError("Workspace slug not found in config.yaml.")

    chat_url = f"{base_url}/workspace/{workspace_slug}/chat"

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key,
    }

    return headers, chat_url


def get_openai_client() -> Optional[OpenAI]:
    """Lazily initialize and return the OpenAI client."""
    global _openai_client
    if _openai_client is None:
        _openai_client = init_openai()
    return _openai_client


def get_groq_client() -> Optional[Groq]:
    """Lazily initialize and return the Groq client."""
    global _groq_client
    if _groq_client is None:
        _groq_client = init_groq()
    return _groq_client


def get_anythingllm_client():
    headers, chat_url = init_anythingllm()
    return headers, chat_url


def test_openai():
    """Test OpenAI API connectivity with a simple chat completion call."""
    client = get_openai_client()
    if not client:
        raise RuntimeError("OpenAI client not available")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello, world!"}],
            max_tokens=5,
        )
        text = response.choices[0].message.content.strip()
        logging.info(f"OpenAI API test successful: {text}")
        # print(f"OpenAI API test successful: {text}")  # Removed for production
    except Exception as e:
        logging.error("OpenAI API test failed: %s", e)
        raise


def test_groq():
    """Test Groq API connectivity with a simple chat completion call."""
    client = get_groq_client()
    if not client:
        raise RuntimeError("Groq client not available")

    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODELS["groq"],
            messages=[{"role": "user", "content": "Hello, world!"}],
        )
        text = response.choices[0].message.content.strip()
        logging.info(f"Groq API test successful: {text}")
        print(f"Groq API test successful: {text}")
    except Exception as e:
        logging.error("Groq API test failed: %s", e)
        raise


def query_gpt(
    prompt: str,
    model: Optional[str] = None,
    provider: Optional[Literal["openai", "groq", "anythingllm"]] = None,
) -> str:
    """Send a prompt to the LLM API and return the generated text, with retry on rate limits.

    Args:
        prompt: The text prompt to send
        model: Specific model to use (optional, will use default for provider)
        provider: Which provider to use ("openai" or "groq", defaults to groq)

    Returns:
        Generated text response
    """
    global _last_groq_request_time

    # Determine provider
    if provider is None:
        provider = DEFAULT_PROVIDER

    # Determine model
    if model is None:
        if provider in ["openai", "groq"]:
            model = DEFAULT_MODELS.get(provider)
            if not model:
                raise ValueError(f"No default model configured for provider: {provider}")
        
    # Get appropriate client
    if provider == "openai":
        client = get_openai_client()
        if not client:
            raise RuntimeError("OpenAI client not available")
    elif provider == "groq":
        client = get_groq_client()
        if not client:
            raise RuntimeError("Groq client not available")

        # Rate limiting for Groq free tier
        current_time = time.time()
        time_since_last = current_time - _last_groq_request_time
        if time_since_last < _groq_min_interval:
            sleep_time = _groq_min_interval - time_since_last
            logging.info(
                f"Rate limiting: waiting {sleep_time:.1f}s before Groq request"
            )
            time.sleep(sleep_time)
        _last_groq_request_time = time.time()
    elif provider == "anythingllm":
        headers, chat_url = get_anythingllm_client()
        if not headers or not chat_url:
            raise RuntimeError("AnythingLLM client not available")
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    logging.debug(f"Sending prompt to {provider} {model}: {prompt[:100]}...")

    for retry in range(_max_retries):
        try:
            if provider in ["openai", "groq"]:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                )
                content = response.choices[0].message.content
                if content is None:
                    logging.warning(f"{provider} API returned None content")
                    return ""

                result = content.strip()
                logging.debug(f"{provider} API response: {result[:100]}...")
                return result
            elif provider == "anythingllm":
                data = {
                    "message": prompt,
                    "mode": "chat",
                    "sessionId": "example-session-id",
                    "attachments": []
                }
                response = requests.post(
                    chat_url,
                    headers=headers,
                    json=data
                )
                if response.status_code != 200:
                    logging.error(
                        f"AnythingLLM API call failed: {response.status_code} {response.text}"
                    )
                    return

                result = response.json().get("textResponse").strip()
                logging.debug(f"AnythingLLM API response: {result[:100]}...")
                return result

        except Exception as e:
            # Handle rate limiting for both providers
            is_rate_limit = False
            if provider == "openai" and OPENAI_AVAILABLE:
                if hasattr(_openai_module.error, "RateLimitError") and isinstance(
                    e, _openai_module.error.RateLimitError
                ):
                    is_rate_limit = True
            elif provider == "groq":
                # Groq rate limiting detection - check for various rate limit indicators
                error_str = str(e).lower()
                if any(
                    indicator in error_str
                    for indicator in ["rate limit", "429", "too many requests", "quota"]
                ):
                    is_rate_limit = True

            if is_rate_limit:
                # Exponential backoff with longer delays for Groq
                if provider == "groq":
                    base_wait = (
                        10.0 if GROQ_FREE_TIER_MODE else 5.0
                    )  # Longer wait for free tier
                else:
                    base_wait = 2.0
                wait = base_wait * (_backoff_factor**retry)
                logging.warning(
                    f"Rate limit reached for {provider}, retrying in {wait:.1f} seconds (retry {retry+1}/{_max_retries})"
                )
                time.sleep(wait)

                # Update last request time for Groq
                if provider == "groq":
                    _last_groq_request_time = time.time()
                continue

            logging.error(f"{provider} API call failed: {e}")
            raise

    # If we exit loop without return, retries exhausted
    raise RuntimeError(f"Max retries exceeded for {provider} query_gpt")


# Backward compatibility functions
def get_client():
    """Backward compatibility function - returns the default provider client."""
    if DEFAULT_PROVIDER == "groq":
        return get_groq_client()
    else:
        return get_openai_client()
