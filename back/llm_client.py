import os
import logging
from typing import Optional, Literal
import time
from datetime import datetime


import json
import requests
import threading
import time
import yaml

def get_appdata_dir():
    appdata = os.getenv("APPDATA") or os.path.expanduser("~")
    app_dir = os.path.join(appdata, "FormFillerAI")
    if not os.path.exists(app_dir):
        os.makedirs(app_dir)
    return app_dir

API_KEYS_PATH = os.path.join(get_appdata_dir(), "api_keys.json")
LOG_PATH = os.path.join(get_appdata_dir(), "logs")
print(f"API Keys path: {API_KEYS_PATH}")
print(f"Logs directory: {LOG_PATH}")

try:
    from back.local_llm import response as local_chat_response
    LOCAL_CHAT_AVAILABLE = True
except ImportError:
    LOCAL_CHAT_AVAILABLE = False
    logging.warning("Local chat module not available")

# Try to import both clients
try:
    from openai import OpenAI
    import openai as _openai_module

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI package not available")
import uuid

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

# Global lock to ensure only one query_gpt call at a time
_query_gpt_lock = threading.Lock()

# Default provider and model configurations
DEFAULT_PROVIDER = "openai"  # Changed default to groq
DEFAULT_MODELS = {
    "openai": "gpt-4.1-mini",
    "groq": "llama-3.3-70b-versatile",
}

LOCAL_MODELS_URL = "http://localhost:8081/generate-response"

# Logging configuration
def _ensureLOG_PATHectory():
    """Ensure the logs directory exists."""
    if not os.path.exists(LOG_PATH):
        os.makedirs(LOG_PATH)

def _get_log_file_path(provider: str, model: str) -> str:
    """Generate log file path for a specific provider and model."""
    _ensureLOG_PATHectory()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_model = model.replace("/", "_").replace(":", "_") if model else "unknown"
    filename = f"{provider}_{safe_model}_{timestamp}.log"
    return os.path.join(LOG_PATH, filename)

def _get_or_create_logger(provider: str) -> logging.Logger:
    """Get or create a logger for a specific provider."""
    logger_name = f"llm_{provider}"
    
    # Check if logger already exists
    if logger_name in logging.Logger.manager.loggerDict:
        return logging.getLogger(logger_name)
    
    # Create new logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    
    # Create file handler if it doesn't exist
    log_file_path = _get_log_file_path(provider, "generic")
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    logger.propagate = False  # Prevent duplicate logs
    
    return logger

def _log_prompt_and_response(provider: str, prompt: str, response: str, duration: float = None):
    """Log the prompt and response to the provider-specific log file."""
    logger = _get_or_create_logger(provider)
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "provider": provider,
        "prompt_length": len(prompt),
        "response_length": len(response),
        "duration_seconds": duration,
        "prompt": prompt,
        "response": response,
    }
    
    logger.info(f"QUERY: {json.dumps(log_entry, ensure_ascii=False, indent=2)}")

def _log_failed_response(provider: str, prompt: str, error_message: str, duration: float = None, **kwargs):
    """Log failed responses with error details to the provider-specific log file."""
    logger = _get_or_create_logger(provider)
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "provider": provider,
        "prompt_length": len(prompt),
        "duration_seconds": duration,
        "prompt": prompt,
        "error_message": error_message,
        "status": "FAILED",
        **kwargs
    }
    
    logger.error(f"FAILED_QUERY: {json.dumps(log_entry, ensure_ascii=False, indent=2)}")


def get_active_api_key(provider: str) -> Optional[str]:
    """Retrieve the API key for the given provider."""
    try:
        with open(API_KEYS_PATH, "r") as file:
            api_keys = json.load(file)
            for key in api_keys:
                if key["provider"] == provider:
                    return key["key"]
    except FileNotFoundError:
        logging.error(f"API keys file not found at {API_KEYS_PATH}")
    except Exception as e:
        logging.error(f"Failed to read API keys: {e}")
    return None

# Update init_openai to use the simplified API key structure
def init_openai() -> Optional[OpenAI]:
    """Initialize OpenAI API client using the API key."""
    if not OPENAI_AVAILABLE:
        logging.error("OpenAI package not installed")
        return None

    api_key = get_active_api_key("openai")
    if not api_key:
        logging.warning("No OpenAI API key found.")
        return None

    try:
        client = OpenAI(api_key=api_key)
        return client
    except Exception as e:
        logging.error(f"Failed to initialize OpenAI client: {e}")
        return None

# Update init_groq to use the simplified API key structure
def init_groq() -> Optional[Groq]:
    """Initialize Groq API client using the API key."""
    if not GROQ_AVAILABLE:
        logging.error("Groq package not installed")
        return None

    api_key = get_active_api_key("groq")
    if not api_key:
        logging.warning("No Groq API key found.")
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
        with open("./back/config.yaml", "r") as file:
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
        _log_failed_response("openai", "Hello, world!", f"OpenAI API test failed: {e}")
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
        _log_failed_response("groq", "Hello, world!", f"Groq API test failed: {e}")
        logging.error("Groq API test failed: %s", e)
        raise


def query_gpt(
    prompt: str,
    model: Optional[str] = None,
    provider: Optional[Literal["openai", "groq", "anythingllm", "locql"]] = None,
) -> str:
    """Send a prompt to the LLM API and return the generated text, with retry on rate limits.

    Args:
        prompt: The text prompt to send
        model: Specific model to use (optional, will use default for provider)
        provider: Which provider to use ("openai" or "groq", defaults to groq)

    Returns:
        Generated text response
    """
    start_time = time.time()
    call_start_timestamp = datetime.now().isoformat()
    
    # Determine provider for logging    
    effective_provider = provider or DEFAULT_PROVIDER
    logger = _get_or_create_logger(effective_provider)
    
    # Log when query_gpt is called
    logger.info(f"query_gpt STARTED at {call_start_timestamp} - provider: {provider}, model: {model}, prompt_length: {len(prompt)}")

    # Check if lock is already acquired (blocking detection)
    if not _query_gpt_lock.acquire(blocking=False):
        logger.info(f"query_gpt call blocked - waiting for previous {provider} call to complete")
        # Now acquire with blocking=True to wait
        _query_gpt_lock.acquire(blocking=True)
        logger.info(f"query_gpt lock acquired - proceeding with {provider} call")
    else:
        logger.debug(f"query_gpt lock acquired immediately for {provider} call")
    
    try:
        result = _query_gpt_internal(prompt, model, provider)
        
        # Log successful completion
        end_time = time.time()
        total_duration = end_time - start_time
        call_end_timestamp = datetime.now().isoformat()
        logger.info(f"query_gpt COMPLETED at {call_end_timestamp} - provider: {provider}, duration: {total_duration:.2f}s, response_length: {len(result) if result else 0}")
        
        return result
        
    except Exception as e:
        # Log failed completion
        end_time = time.time()
        total_duration = end_time - start_time
        call_end_timestamp = datetime.now().isoformat()
        logger.error(f"query_gpt FAILED at {call_end_timestamp} - provider: {provider}, duration: {total_duration:.2f}s, error: {str(e)}")
        raise
        
    finally:
        _query_gpt_lock.release()
        logger.debug(f"query_gpt lock released for {provider} call")


def _query_gpt_internal(
    prompt: str,
    model: Optional[str] = None,
    provider: Optional[Literal["openai", "groq", "anythingllm"]] = None,
) -> str:
    """Internal implementation of query_gpt that performs the actual API call."""
    global _last_groq_request_time

    start_time = time.time()
    
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
    elif provider == "local":
        # For local models, use the chat response function
        if not LOCAL_CHAT_AVAILABLE:
            raise RuntimeError("Local chat module not available")
        if not prompt:
            raise ValueError("Prompt must be provided for local model queries")
        
        try:
            result = local_chat_response(prompt)
            if result is None:
                duration = time.time() - start_time
                error_msg = "Local model returned None response"
                _log_failed_response("local", prompt, error_msg, duration)
                logging.error(error_msg)
                return ""
            
            result = result.strip()
            duration = time.time() - start_time
            _log_prompt_and_response("local", prompt, result, duration)
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Local model call failed: {str(e)}"
            _log_failed_response("local", prompt, error_msg, duration, exception_type=type(e).__name__)
            logging.error(error_msg)
            return ""
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    logging.debug(f"Sending prompt to {provider} {model}: {prompt}...")

    for retry in range(_max_retries):
        try:
            if provider in ["openai", "groq"]:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                )
                content = response.choices[0].message.content
                if content is None:
                    duration = time.time() - start_time
                    error_msg = f"{provider} API returned None content"
                    _log_failed_response(provider, prompt, error_msg, duration)
                    logging.warning(error_msg)
                    return ""

                result = content.strip()
                duration = time.time() - start_time
                _log_prompt_and_response(provider, prompt, result, duration)
                logging.debug(f"{provider} API response: {result}...")
                return result
            elif provider == "anythingllm":
                data = {
                    "message": prompt,
                    "mode": "chat",
                    "sessionId": str(uuid.uuid4()),
                    "attachments": []
                }
                response = requests.post(
                    chat_url,
                    headers=headers,
                    json=data
                )
                if response.status_code != 200:
                    duration = time.time() - start_time
                    error_msg = f"AnythingLLM API call failed: {response.status_code} {response.text}"
                    _log_failed_response("anythingllm", prompt, error_msg, duration,
                                       status_code=response.status_code, response_text=response.text)
                    logging.error(error_msg)
                    return ""

                result = response.json().get("textResponse").strip()
                duration = time.time() - start_time
                _log_prompt_and_response("anythingllm", prompt, result, duration)
                logging.debug(f"AnythingLLM API response: {result}...")
                return result
            elif provider == "local":
                # For local models, use the chat response function
                if not LOCAL_CHAT_AVAILABLE:
                    raise RuntimeError("Local chat module not available")
                
                result = local_chat_response(prompt)
                if result is None:
                    duration = time.time() - start_time
                    error_msg = "Local model returned None response"
                    _log_failed_response("local", prompt, error_msg, duration)
                    logging.error(error_msg)
                    return ""
                
                result = result.strip()
                duration = time.time() - start_time
                _log_prompt_and_response("local", prompt, result, duration)
                return result


        except Exception as e:
            duration = time.time() - start_time
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
                # Log rate limit as failed attempt
                _log_failed_response(provider, prompt, f"Rate limit exceeded: {str(e)}", 
                                   duration, retry_attempt=retry + 1, rate_limit=True)
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

            # Log non-rate-limit API failures
            _log_failed_response(provider, prompt, f"API call exception: {str(e)}", 
                               duration, retry_attempt=retry + 1, exception_type=type(e).__name__)
            logging.error(f"{provider} API call failed: {e}")
            raise

    # If we exit loop without return, retries exhausted
    duration = time.time() - start_time
    error_msg = f"Max retries exceeded for {provider} query_gpt"
    _log_failed_response(provider, prompt, error_msg, duration, max_retries_exceeded=True)
    raise RuntimeError(error_msg)


# Backward compatibility functions
def get_client():
    """Backward compatibility function - returns the default provider client."""
    if DEFAULT_PROVIDER == "groq":
        return get_groq_client()
    else:
        return get_openai_client()
