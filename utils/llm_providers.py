"""
LLM Provider utilities for grading documents.
This module consolidates all LLM provider logic to eliminate redundancy.
"""

import json
import os
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager

import google.generativeai as genai
import openai
import requests
from anthropic import Anthropic
from openai import OpenAI

# Optional Redis import for distributed semaphore
_redis_available = False
_redis_client = None
try:
    import redis

    _redis_available = True
except Exception:
    _redis_available = False

_DEFAULT_PROPRIETARY_CONCURRENCY = int(
    os.getenv("DEFAULT_PROPRIETARY_CONCURRENCY", "4")
)
_DEFAULT_LOCAL_CONCURRENCY = int(os.getenv("DEFAULT_LOCAL_CONCURRENCY", "1"))
_PROPRIETARY_PROVIDERS = {"OpenRouter", "Claude", "Gemini", "OpenAI", "Chutes", "Z.AI", "NanoGPT", "Z.AI Coding Plan"}
_LOCAL_PROVIDERS = {"LM Studio", "Ollama"}

_provider_semaphores = {}
_provider_limits = {}


def _get_provider_limit(provider_name):
    """
    Determine concurrency limit for a provider.

    Resolution order:
    1. Environment variable PROVIDER_MAX_<PROVIDER_NAME_UPPER> (spaces -> _)
       e.g. PROVIDER_MAX_CLAUDE=6
    2. JSON mapping in PROVIDER_MAX_PARALLEL (env), e.g. {"Claude": 6, "LM Studio": 1}
    3. Defaults based on provider type (proprietary/local)
    """
    # Per-provider env var override
    env_key = f"PROVIDER_MAX_{provider_name.upper().replace(' ', '_')}"
    if env_key in os.environ:
        try:
            return int(os.environ[env_key])
        except Exception:
            pass

    # JSON mapping override
    mapping = os.getenv("PROVIDER_MAX_PARALLEL")
    if mapping:
        try:
            parsed = json.loads(mapping)
            if provider_name in parsed:
                return int(parsed[provider_name])
            # Support lower-case keys as well
            if provider_name.lower() in parsed:
                return int(parsed[provider_name.lower()])
        except Exception:
            # Ignore parse errors and fall through to defaults
            pass

    # Defaults
    if provider_name in _PROPRIETARY_PROVIDERS:
        return _DEFAULT_PROPRIETARY_CONCURRENCY
    if provider_name in _LOCAL_PROVIDERS:
        return _DEFAULT_LOCAL_CONCURRENCY
    # Fallback to proprietary default for unknown providers
    return _DEFAULT_PROPRIETARY_CONCURRENCY


def _get_or_create_semaphore(provider_name):
    """Lazily create a bounded semaphore for a provider with the configured limit.
    Chooses Redis-backed semaphore if configured, otherwise falls back to in-process semaphore.
    """
    if provider_name in _provider_semaphores:
        return _provider_semaphores[provider_name]

    limit = _get_provider_limit(provider_name)

    # If Redis is requested/available, create a RedisSemaphore
    use_redis = False
    if os.getenv("USE_REDIS_SEMAPHORE", "").lower() in ("1", "true", "yes"):
        use_redis = True
    if os.getenv("REDIS_URL"):
        use_redis = True

    if use_redis and _redis_available:
        # Initialize global redis client lazily
        global _redis_client
        if _redis_client is None:
            try:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                _redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
            except Exception:
                _redis_client = None

        if _redis_client:
            sem = RedisSemaphore(
                _redis_client,
                provider_name,
                limit,
                ttl=int(os.getenv("PROVIDER_SEMAPHORE_TTL", "300")),
            )
            _provider_semaphores[provider_name] = sem
            _provider_limits[provider_name] = limit
            return sem
        else:
            # Fall through to in-process semaphore if redis init failed
            pass

    # Fall back to in-process semaphore
    sem = threading.BoundedSemaphore(limit)
    _provider_semaphores[provider_name] = sem
    _provider_limits[provider_name] = limit
    return sem


# Redis-backed semaphore implementation
class RedisSemaphore:
    """
    A simple Redis-backed semaphore using an atomic Lua script.
    Keys:
      - counter key: stores current count
    Notes:
      - This semaphore is lightweight and per-key; it does not track holders individually.
      - TTL is applied to the counter to avoid stale locks if a process dies without releasing,
        but this means a semaphore count can reset after TTL seconds if all processes fail to release.
      - This is suitable for limiting parallel requests across processes but not for strong leader-election.
    """

    _ACQUIRE_LUA = (
        "local current = tonumber(redis.call('get', KEYS[1]) or '0')\n"
        "if current < tonumber(ARGV[1]) then\n"
        "    current = redis.call('incr', KEYS[1])\n"
        "    redis.call('expire', KEYS[1], ARGV[2])\n"
        "    return 1\n"
        "else\n"
        "    return 0\n"
        "end"
    )

    _RELEASE_LUA = (
        "local current = tonumber(redis.call('get', KEYS[1]) or '0')\n"
        "if current > 0 then\n"
        "    redis.call('decr', KEYS[1])\n"
        "    return 1\n"
        "else\n"
        "    return 0\n"
        "end"
    )

    def __init__(self, client, name, limit, ttl=300):
        self.client = client
        self.name = name
        self.limit = int(limit)
        self.ttl = int(ttl)
        self.counter_key = f"semaphore:{self.name}:counter"
        try:
            self._acquire_script = client.register_script(self._ACQUIRE_LUA)
            self._release_script = client.register_script(self._RELEASE_LUA)
        except Exception:
            # redis-py clients sometimes don't support register_script in certain configs;
            # fall back to EVAL if necessary by storing None and using eval directly.
            self._acquire_script = None
            self._release_script = None

    def acquire(self, timeout=300, sleep_interval=0.1):
        """Try to acquire the semaphore within timeout seconds."""
        import time

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if self._acquire_script:
                    res = self._acquire_script(
                        keys=[self.counter_key], args=[self.limit, self.ttl]
                    )
                else:
                    res = self.client.eval(
                        self._ACQUIRE_LUA, 1, self.counter_key, self.limit, self.ttl
                    )
                if int(res) == 1:
                    return True
            except Exception:
                # On any redis error, break and fallback to failure to avoid hanging
                return False
            time.sleep(sleep_interval)
        return False

    def release(self):
        """Release one slot in the semaphore."""
        try:
            if self._release_script:
                res = self._release_script(keys=[self.counter_key], args=[])
            else:
                res = self.client.eval(self._RELEASE_LUA, 1, self.counter_key)
            return int(res) == 1
        except Exception:
            # Suppress errors to avoid masking original exceptions
            return False


@contextmanager
def provider_semaphore(provider_name):
    """
    Context manager that acquires/releases a semaphore for the given provider.
    Waits up to PROVIDER_SEMAPHORE_TIMEOUT seconds (default 300) to acquire; raises TimeoutError if not acquired.
    Uses Redis-backed semaphore when configured; otherwise uses an in-process threading semaphore.
    """
    timeout = int(os.getenv("PROVIDER_SEMAPHORE_TIMEOUT", "300"))
    sem = _get_or_create_semaphore(provider_name)

    # If using RedisSemaphore, it exposes acquire/release methods.
    acquired = False
    try:
        if isinstance(sem, RedisSemaphore):
            acquired = sem.acquire(timeout=timeout)
            if not acquired:
                raise TimeoutError(
                    f"Timeout acquiring redis semaphore for provider {provider_name}"
                )
            yield
        else:
            acquired = sem.acquire(timeout=timeout)
            if not acquired:
                raise TimeoutError(
                    f"Timeout acquiring local semaphore for provider {provider_name}"
                )
            yield
    finally:
        if acquired:
            try:
                if isinstance(sem, RedisSemaphore):
                    sem.release()
                else:
                    sem.release()
            except Exception:
                # Best-effort release; ignore to avoid masking original exceptions
                pass


# Backward compatibility wrapper functions
def grade_with_openrouter(
    text,
    prompt,
    model="anthropic/claude-opus-4-1",
    marking_scheme_content=None,
    temperature=0.3,
    max_tokens=2000,
):
    """Backward compatibility wrapper for OpenRouter grading."""
    provider = OpenRouterLLMProvider()
    return provider.grade_document(
        text, prompt, model, marking_scheme_content, temperature, max_tokens
    )


def grade_with_claude(
    text,
    prompt,
    model="claude-4-opus-20250805",
    marking_scheme_content=None,
    temperature=0.3,
    max_tokens=2000,
):
    """Backward compatibility wrapper for Claude grading."""
    provider = ClaudeLLMProvider()
    return provider.grade_document(
        text, prompt, model, marking_scheme_content, temperature, max_tokens
    )


def grade_with_lm_studio(
    text,
    prompt,
    model="local-model",
    marking_scheme_content=None,
    temperature=0.3,
    max_tokens=2000,
):
    """Backward compatibility wrapper for LM Studio grading."""
    provider = LMStudioLLMProvider()
    return provider.grade_document(
        text, prompt, model, marking_scheme_content, temperature, max_tokens
    )


def grade_with_gemini(
    text,
    prompt,
    model="gemini-2.5-pro",
    marking_scheme_content=None,
    temperature=0.3,
    max_tokens=2000,
):
    """Backward compatibility wrapper for Gemini grading."""
    provider = GeminiLLMProvider()
    return provider.grade_document(
        text, prompt, model, marking_scheme_content, temperature, max_tokens
    )


def grade_with_openai(
    text,
    prompt,
    model="gpt-5",
    marking_scheme_content=None,
    temperature=0.3,
    max_tokens=2000,
):
    """Backward compatibility wrapper for OpenAI grading."""
    provider = OpenAILLMProvider()
    return provider.grade_document(
        text, prompt, model, marking_scheme_content, temperature, max_tokens
    )


class LLMProvider(ABC):
    """Abstract Base Class for LLM Providers."""

    @abstractmethod
    def grade_document(
        self,
        text,
        prompt,
        model=None,
        marking_scheme_content=None,
        temperature=0.3,
        max_tokens=2000,
    ):
        """
        Abstract method to grade a document using the LLM provider.
        Implementations should handle API calls, error handling, and response parsing.

        Parameters:
          - text: The document text to grade.
          - prompt: The grading instructions / prompt.
          - model: Optional provider-specific model identifier (e.g. 'gpt-4o', 'claude-4-opus-20250805').
          - marking_scheme_content: Optional marking scheme text to include.
          - temperature: Model temperature.
          - max_tokens: Maximum tokens for the response.
        """


class OpenRouterLLMProvider(LLMProvider):
    """LLM Provider for OpenRouter API."""

    def get_available_models(self):
        """Fetch available models from OpenRouter API."""
        try:
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            if not openrouter_key:
                return {"success": False, "error": "API key not configured"}

            headers = {
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json",
            }

            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                models_data = response.json()
                models = []
                for model in models_data.get("data", []):
                    models.append({
                        "id": model["id"],
                        "name": model.get("name", model["id"]),
                        "description": model.get("description", ""),
                        "pricing": model.get("pricing", {}),
                        "context_length": model.get("context_length", 0),
                        "provider": model.get("provider", "")
                    })
                return {"success": True, "models": models}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def grade_document(
        self,
        text,
        prompt,
        model="anthropic/claude-opus-4-1",
        marking_scheme_content=None,
        temperature=0.3,
        max_tokens=2000,
    ):
        try:
            # Re-check environment each call to satisfy tests that clear env
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            if not openrouter_key:
                return {
                    "success": False,
                    "error": "OpenRouter API authentication failed. "
                    "Please check your API key configuration.",
                    "provider": "OpenRouter",
                }

            # Prepare the grading prompt with marking scheme if provided
            if marking_scheme_content:
                enhanced_prompt = (
                    f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}"
                    f"\n\nPlease use the above marking scheme to grade the following document:\n{text}"
                )
            else:
                enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

            # Use requests library for OpenRouter API to avoid OpenAI SDK compatibility issues
            headers = {
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria.",
                    },
                    {"role": "user", "content": enhanced_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )

            # Handle success and non-200 responses explicitly so we can return
            # helpful error messages (e.g. include response body for 4xx/5xx).
            if response.status_code == 200:
                result = response.json()
                grade_text = result["choices"][0]["message"]["content"]
                usage = result.get("usage")
            else:
                # Attempt to decode body for debugging; fall back to raw text.
                try:
                    body = response.json()
                except Exception:
                    body = response.text
                return {
                    "success": False,
                    "error": f"OpenRouter API error: {response.status_code} - {body}",
                    "provider": "OpenRouter",
                }

            return {
                "success": True,
                "grade": grade_text,
                "model": model,
                "provider": "OpenRouter",
                "usage": usage,
            }
        except Exception as e:
            error_msg = str(e)
            if "auth" in error_msg.lower() or "key" in error_msg.lower():
                return {
                    "success": False,
                    "error": "OpenRouter API authentication failed. Please check your API key.",
                    "provider": "OpenRouter",
                }
            elif "rate" in error_msg.lower() and "limit" in error_msg.lower():
                return {
                    "success": False,
                    "error": "OpenRouter API rate limit exceeded. Please try again later.",
                    "provider": "OpenRouter",
                }
            else:
                return {
                    "success": False,
                    "error": f"Unexpected error with OpenRouter API: {error_msg}",
                    "provider": "OpenRouter",
                }


class ClaudeLLMProvider(LLMProvider):
    """LLM Provider for Claude API."""

    def get_available_models(self):
        """Fetch available models from Claude API."""
        try:
            claude_key = os.getenv("CLAUDE_API_KEY")
            if not claude_key:
                return {"success": False, "error": "API key not configured"}

            anthropic = Anthropic(api_key=claude_key)
            models = anthropic.models.list()

            model_list = []
            for model in models.data:
                model_list.append({
                    "id": model.id,
                    "name": model.display_name or model.id,
                    "description": "",
                    "context_length": model.max_tokens,
                    "provider": "Anthropic"
                })
            return {"success": True, "models": model_list}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def grade_document(
        self,
        text,
        prompt,
        model="claude-4-opus-20250805",
        marking_scheme_content=None,
        temperature=0.3,
        max_tokens=2000,
    ):
        # Re-check environment each call to satisfy tests that clear env
        claude_key = os.getenv("CLAUDE_API_KEY")
        if not claude_key:
            return {
                "success": False,
                "error": "Claude API not configured or failed to initialize",
                "provider": "Claude",
            }

        # Create client when key is present
        try:
            anthropic = Anthropic(api_key=claude_key)
        except Exception:
            return {
                "success": False,
                "error": "Claude API not configured or failed to initialize",
                "provider": "Claude",
            }

        try:
            # Prepare the grading prompt with marking scheme if provided
            if marking_scheme_content:
                enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
            else:
                enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

            response = anthropic.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system="You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria.",
                messages=[{"role": "user", "content": enhanced_prompt}],
            )

            return {
                "success": True,
                "grade": response.content[0].text,
                "model": model,
                "provider": "Claude",
                "usage": response.usage.model_dump() if response.usage else None,
            }
        except Exception as e:
            error_msg = str(e)
            if "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
                return {
                    "success": False,
                    "error": "Claude API authentication failed. Please check your API key.",
                    "provider": "Claude",
                }
            elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
                return {
                    "success": False,
                    "error": "Claude API rate limit exceeded. Please try again later.",
                    "provider": "Claude",
                }
            elif "timeout" in error_msg.lower():
                return {
                    "success": False,
                    "error": "Claude API request timed out. Please try again.",
                    "provider": "Claude",
                }
            else:
                return {
                    "success": False,
                    "error": f"Claude API error: {error_msg}",
                    "provider": "Claude",
                }


class LMStudioLLMProvider(LLMProvider):
    """LLM Provider for LM Studio API."""

    def get_available_models(self):
        """Fetch available models from LM Studio API."""
        try:
            lm_studio_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")

            response = requests.get(
                f"{lm_studio_url}/models",
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if response.status_code == 200:
                models_data = response.json()
                models = []
                for model in models_data.get("data", []):
                    models.append({
                        "id": model["id"],
                        "name": model.get("name", model["id"]),
                        "description": model.get("description", ""),
                        "provider": "LM Studio"
                    })
                return {"success": True, "models": models}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def grade_document(
        self,
        text,
        prompt,
        model="local-model",
        marking_scheme_content=None,
        temperature=0.3,
        max_tokens=2000,
    ):
        # Get URL from environment variable, don't use cached module-level variable for testing
        lm_studio_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")

        try:
            # Prepare the grading prompt with marking scheme if provided
            if marking_scheme_content:
                enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
            else:
                enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

            response = requests.post(
                f"{lm_studio_url}/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria.",
                        },
                        {"role": "user", "content": enhanced_prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                headers={"Content-Type": "application/json"},
                timeout=120,
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "grade": result["choices"][0]["message"]["content"],
                    "model": model,
                    "provider": "LM Studio",
                    "usage": result.get("usage"),
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": "LM Studio endpoint not found. Please check if LM Studio is running and the URL is correct.",
                    "provider": "LM Studio",
                }
            elif response.status_code == 500:
                return {
                    "success": False,
                    "error": "LM Studio internal server error. Please check LM Studio logs.",
                    "provider": "LM Studio",
                }
            else:
                return {
                    "success": False,
                    "error": f"LM Studio API error: {response.status_code} - {response.text}",
                    "provider": "LM Studio",
                }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": f"Could not connect to LM Studio at {lm_studio_url}. Please check if LM Studio is running.",
                "provider": "LM Studio",
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "LM Studio request timed out. Please try again.",
                "provider": "LM Studio",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"LM Studio API error: {str(e)}",
                "provider": "LM Studio",
            }


class OllamaLLMProvider(LLMProvider):
    """LLM Provider for Ollama API."""

    def get_available_models(self):
        """Fetch available models from Ollama API."""
        try:
            ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

            response = requests.get(
                f"{ollama_url}/api/tags",
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if response.status_code == 200:
                models_data = response.json()
                models = []
                for model in models_data.get("models", []):
                    models.append({
                        "id": model["name"],
                        "name": model["name"],
                        "description": f"{model.get('details', {}).get('description', '')} - Size: {model.get('size', 0)}GB",
                        "provider": "Ollama"
                    })
                return {"success": True, "models": models}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def grade_document(
        self,
        text,
        prompt,
        model="llama2",
        marking_scheme_content=None,
        temperature=0.3,
        max_tokens=2000,
    ):
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

        try:
            if marking_scheme_content:
                enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
            else:
                enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

            # Ollama doesn't directly support system messages in the /api/generate endpoint for all models
            # We can prepend the system message to the user prompt for a similar effect
            full_prompt = (
                "You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria.\n\n"
                + enhanced_prompt
            )

            response = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                    "temperature": temperature,
                    "options": {
                        "num_predict": max_tokens
                    },  # Ollama uses num_predict for max_tokens
                },
                headers={"Content-Type": "application/json"},
                timeout=120,
            )

            if response.status_code == 200:
                result = response.json()
                # Ollama may return the output under different keys depending on model/version.
                # Support common shapes used in tests and local responses:
                # - {'response': 'Grade: A', 'prompt_eval_count': X, 'eval_count': Y}
                # - {'choices': [{'message': {'content': '...'}}], ...}
                # - {'text': '...'}
                grade_text = None
                if isinstance(result, dict):
                    grade_text = result.get("response") or result.get("text")
                    # choices -> message -> content
                    if (
                        not grade_text
                        and "choices" in result
                        and isinstance(result["choices"], list)
                        and len(result["choices"]) > 0
                    ):
                        try:
                            grade_text = result["choices"][0]["message"]["content"]
                        except Exception:
                            # defensive: try other nested locations
                            try:
                                grade_text = result["choices"][0].get("text")
                            except Exception:
                                grade_text = None
                # Fallback to stringifying result if nothing found
                if not grade_text:
                    try:
                        grade_text = str(result)
                    except Exception:
                        grade_text = ""

                prompt_count = (
                    result.get("prompt_eval_count", 0)
                    if isinstance(result, dict)
                    else 0
                )
                eval_count = (
                    result.get("eval_count", 0) if isinstance(result, dict) else 0
                )

                return {
                    "success": True,
                    "grade": grade_text,
                    "model": model,
                    "provider": "Ollama",
                    "usage": {
                        "prompt_tokens": prompt_count,
                        "completion_tokens": eval_count,
                        "total_tokens": (prompt_count or 0) + (eval_count or 0),
                    },
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": "Ollama endpoint not found. Please check if Ollama is running and the URL is correct.",
                    "provider": "Ollama",
                }
            elif response.status_code == 500:
                return {
                    "success": False,
                    "error": "Ollama internal server error. Please check Ollama logs.",
                    "provider": "Ollama",
                }
            else:
                return {
                    "success": False,
                    "error": f"Ollama API error: {response.status_code} - {response.text}",
                    "provider": "Ollama",
                }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": f"Could not connect to Ollama at {ollama_url}. Please check if Ollama is running.",
                "provider": "Ollama",
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Ollama request timed out. Please try again.",
                "provider": "Ollama",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Ollama API error: {str(e)}",
                "provider": "Ollama",
            }


class GeminiLLMProvider(LLMProvider):
    """LLM Provider for Google Gemini API."""

    def get_available_models(self):
        """Fetch available models from Gemini API."""
        try:
            gemini_key = os.getenv("GEMINI_API_KEY")
            if not gemini_key:
                return {"success": False, "error": "API key not configured"}

            genai.configure(api_key=gemini_key)

            # List available models
            models = []
            for model in genai.list_models():
                if "generateContent" in model.supported_generation_methods:
                    models.append({
                        "id": model.name,
                        "name": model.display_name or model.name,
                        "description": model.description or "",
                        "provider": "Google"
                    })
            return {"success": True, "models": models}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def grade_document(
        self,
        text,
        prompt,
        model="gemini-2.5-pro",
        marking_scheme_content=None,
        temperature=0.3,
        max_tokens=2000,
    ):
        try:
            # Re-check environment each call to satisfy tests that clear env
            gemini_key = os.getenv("GEMINI_API_KEY")
            if not gemini_key:
                return {
                    "success": False,
                    "error": "Gemini API authentication failed. Please check your API key configuration.",
                    "provider": "Gemini",
                }

            # Configure Gemini
            genai.configure(api_key=gemini_key)

            # Prepare the grading prompt with marking scheme if provided
            if marking_scheme_content:
                enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
            else:
                enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

            # Create the model
            gemini_model = genai.GenerativeModel(
                model_name=model,
                system_instruction="You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria.",
            )

            # Generate response
            response = gemini_model.generate_content(
                enhanced_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )

            return {
                "success": True,
                "grade": response.text,
                "model": model,
                "provider": "Gemini",
                "usage": {
                    "prompt_tokens": (
                        response.usage_metadata.prompt_token_count
                        if response.usage_metadata
                        else None
                    ),
                    "completion_tokens": (
                        response.usage_metadata.candidates_token_count
                        if response.usage_metadata
                        else None
                    ),
                    "total_tokens": (
                        response.usage_metadata.total_token_count
                        if response.usage_metadata
                        else None
                    ),
                },
            }
        except Exception as e:
            error_msg = str(e)
            if (
                "authentication" in error_msg.lower()
                or "api_key" in error_msg.lower()
                or "permission" in error_msg.lower()
            ):
                return {
                    "success": False,
                    "error": "Gemini API authentication failed. Please check your API key.",
                    "provider": "Gemini",
                }
            elif (
                "quota" in error_msg.lower()
                or "rate" in error_msg.lower()
                or "limit" in error_msg.lower()
            ):
                return {
                    "success": False,
                    "error": "Gemini API rate limit exceeded. Please try again later.",
                    "provider": "Gemini",
                }
            elif "timeout" in error_msg.lower():
                return {
                    "success": False,
                    "error": "Gemini API request timed out. Please try again.",
                    "provider": "Gemini",
                }
            else:
                return {
                    "success": False,
                    "error": f"Gemini API error: {error_msg}",
                    "provider": "Gemini",
                }


class OpenAILLMProvider(LLMProvider):
    """LLM Provider for OpenAI API (direct, not through OpenRouter)."""

    def get_available_models(self):
        """Fetch available models from OpenAI API."""
        try:
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                return {"success": False, "error": "API key not configured"}

            client = OpenAI(api_key=openai_key)
            models = client.models.list()

            model_list = []
            for model in models.data:
                model_list.append({
                    "id": model.id,
                    "name": model.id,
                    "description": "",
                    "provider": "OpenAI"
                })
            return {"success": True, "models": model_list}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def grade_document(
        self,
        text,
        prompt,
        model="gpt-5",
        marking_scheme_content=None,
        temperature=0.3,
        max_tokens=2000,
    ):
        try:
            # Re-check environment each call to satisfy tests that clear env
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                return {
                    "success": False,
                    "error": "OpenAI API authentication failed. Please check your API key configuration.",
                    "provider": "OpenAI",
                }

            # Create OpenAI client with new SDK
            client = OpenAI(api_key=openai_key)

            # Prepare the grading prompt with marking scheme if provided
            if marking_scheme_content:
                enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
            else:
                enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria.",
                    },
                    {"role": "user", "content": enhanced_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            return {
                "success": True,
                "grade": response.choices[0].message.content,
                "model": model,
                "provider": "OpenAI",
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            }
        except openai.AuthenticationError:
            return {
                "success": False,
                "error": "OpenAI API authentication failed. Please check your API key.",
                "provider": "OpenAI",
            }
        except openai.RateLimitError:
            return {
                "success": False,
                "error": "OpenAI API rate limit exceeded. Please try again later.",
                "provider": "OpenAI",
            }
        except openai.APIError as e:
            return {
                "success": False,
                "error": f"OpenAI API error: {str(e)}",
                "provider": "OpenAI",
            }
        except Exception as e:
            error_msg = str(e)
            if "auth" in error_msg.lower() or "key" in error_msg.lower():
                return {
                    "success": False,
                    "error": "OpenAI API authentication failed. Please check your API key.",
                    "provider": "OpenAI",
                }
            else:
                return {
                    "success": False,
                    "error": f"Unexpected error with OpenAI API: {error_msg}",
                    "provider": "OpenAI",
                }


class ZAICodingPlanLLMProvider(LLMProvider):
    """LLM Provider for Z.AI Coding Plan subscription using Anthropic-compatible endpoint."""

    def get_available_models(self):
        """Return available models for Z.AI Coding Plan."""
        # Z.AI Coding Plan models (limited selection for coding tools)
        models = [
            {"id": "glm-4.6", "name": "GLM-4.6", "description": "Latest flagship model for coding (Coding Plan)", "provider": "Z.AI Coding Plan"},
            {"id": "glm-4.5", "name": "GLM-4.5", "description": "Foundation model for coding (Coding Plan)", "provider": "Z.AI Coding Plan"},
            {"id": "glm-4.5-air", "name": "GLM-4.5 Air", "description": "Lightweight model for auxiliary tasks (Coding Plan)", "provider": "Z.AI Coding Plan"},
        ]
        return {"success": True, "models": models}

    def grade_document(
        self,
        text,
        prompt,
        model="glm-4.6",
        marking_scheme_content=None,
        temperature=0.3,
        max_tokens=2000,
    ):
        """
        Grade document using Z.AI Coding Plan via Anthropic-compatible endpoint.

        Note: This uses Z.AI's Coding Plan subscription which works through
        an Anthropic API-compatible endpoint. Requires active Coding Plan subscription.
        """
        try:
            zai_key = os.getenv("Z_AI_CODING_PLAN_API_KEY")
            if not zai_key:
                return {
                    "success": False,
                    "error": "Z.AI Coding Plan API authentication failed. Please check your API key configuration. Note: This requires an active Z.AI Coding Plan subscription.",
                    "provider": "Z.AI Coding Plan",
                }

            # Prepare the grading prompt with marking scheme if provided
            if marking_scheme_content:
                enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
            else:
                enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

            headers = {
                "x-api-key": zai_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            }

            # Use Anthropic-compatible message format
            payload = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": f"You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria.\n\n{enhanced_prompt}"
                    }
                ]
            }

            response = requests.post(
                "https://api.z.ai/api/anthropic/v1/messages",
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                content = data.get("content", [{}])[0].get("text", "")

                return {
                    "success": True,
                    "grade": content,
                    "model": model,
                    "provider": "Z.AI Coding Plan",
                    "usage": {
                        "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                        "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
                        "total_tokens": data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0),
                    },
                }
            else:
                return {
                    "success": False,
                    "error": f"Z.AI Coding Plan API error: {response.status_code} - {response.text}",
                    "provider": "Z.AI Coding Plan",
                }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Z.AI Coding Plan API connection error: {str(e)}",
                "provider": "Z.AI Coding Plan",
            }
        except Exception as e:
            error_msg = str(e)
            if "auth" in error_msg.lower() or "key" in error_msg.lower() or "unauthorized" in error_msg.lower():
                return {
                    "success": False,
                    "error": "Z.AI Coding Plan API authentication failed. Please check your API key and subscription status.",
                    "provider": "Z.AI Coding Plan",
                }
            else:
                return {
                    "success": False,
                    "error": f"Unexpected error with Z.AI Coding Plan API: {error_msg}",
                    "provider": "Z.AI Coding Plan",
                }


class ChutesLLMProvider(LLMProvider):
    """LLM Provider for Chutes AI platform."""

    def get_available_models(self):
        """Fetch available models from Chutes AI API."""
        try:
            chutes_key = os.getenv("CHUTES_API_KEY")
            if not chutes_key:
                return {"success": False, "error": "API key not configured"}

            headers = {
                "Authorization": f"Bearer {chutes_key}",
                "Content-Type": "application/json",
            }

            response = requests.get(
                "https://api.chutes.ai/v1/models",
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                models_data = response.json()
                models = []
                for model in models_data.get("data", []):
                    models.append({
                        "id": model["id"],
                        "name": model.get("name", model["id"]),
                        "description": model.get("description", ""),
                        "context_length": model.get("context_length", 0),
                        "provider": "Chutes"
                    })
                return {"success": True, "models": models}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def grade_document(
        self,
        text,
        prompt,
        model="microsoft/DialoGPT-medium",
        marking_scheme_content=None,
        temperature=0.3,
        max_tokens=2000,
    ):
        try:
            chutes_key = os.getenv("CHUTES_API_KEY")
            if not chutes_key:
                return {
                    "success": False,
                    "error": "Chutes AI API authentication failed. Please check your API key configuration.",
                    "provider": "Chutes",
                }

            # Prepare the grading prompt with marking scheme if provided
            if marking_scheme_content:
                enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
            else:
                enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

            headers = {
                "Authorization": f"Bearer {chutes_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria.",
                    },
                    {"role": "user", "content": enhanced_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            response = requests.post(
                "https://api.chutes.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "grade": data["choices"][0]["message"]["content"],
                    "model": model,
                    "provider": "Chutes",
                    "usage": {
                        "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                        "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                        "total_tokens": data.get("usage", {}).get("total_tokens", 0),
                    },
                }
            else:
                return {
                    "success": False,
                    "error": f"Chutes AI API error: {response.status_code} - {response.text}",
                    "provider": "Chutes",
                }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Chutes AI API connection error: {str(e)}",
                "provider": "Chutes",
            }
        except Exception as e:
            error_msg = str(e)
            if "auth" in error_msg.lower() or "key" in error_msg.lower():
                return {
                    "success": False,
                    "error": "Chutes AI API authentication failed. Please check your API key.",
                    "provider": "Chutes",
                }
            else:
                return {
                    "success": False,
                    "error": f"Unexpected error with Chutes AI API: {error_msg}",
                    "provider": "Chutes",
                }


class ZAILLMProvider(LLMProvider):
    """LLM Provider for Z.AI platform."""

    def get_available_models(self):
        """Return available models for Z.AI platform."""
        # Z.AI API models (not Coding Plan - those are for coding tools only)
        # Note: Z.AI Coding Plan is separate and only works within coding tools like Claude Code
        # This implementation uses the normal Z.AI API which is billed separately
        models = [
            {"id": "glm-4.6", "name": "GLM-4.6", "description": "Latest flagship model series for agent applications (API)", "provider": "Z.AI"},
            {"id": "glm-4.5", "name": "GLM-4.5", "description": "Foundation model for intelligent agents (API)", "provider": "Z.AI"},
            {"id": "glm-4.5-air", "name": "GLM-4.5 Air", "description": "Lightweight version of GLM-4.5 (API)", "provider": "Z.AI"},
            {"id": "glm-4.5-x", "name": "GLM-4.5 X", "description": "Enhanced version of GLM-4.5 (API)", "provider": "Z.AI"},
            {"id": "glm-4.5-airx", "name": "GLM-4.5 Air X", "description": "Enhanced lightweight version (API)", "provider": "Z.AI"},
            {"id": "glm-4.5-flash", "name": "GLM-4.5 Flash", "description": "Fast response model (API)", "provider": "Z.AI"},
            {"id": "glm-4-32b-0414-128k", "name": "GLM-4-32B-128K", "description": "Highly cost-effective foundation model with 128K context (API)", "provider": "Z.AI"},
        ]
        return {"success": True, "models": models}

    def grade_document(
        self,
        text,
        prompt,
        model="glm-4.6",
        marking_scheme_content=None,
        temperature=0.3,
        max_tokens=2000,
    ):
        """
        Grade document using Z.AI API (not Coding Plan).

        Note: This uses Z.AI's normal API which is billed separately per call.
        The Z.AI Coding Plan is only for use within coding tools like Claude Code
        and cannot be accessed via API calls.
        """
        try:
            zai_key = os.getenv("Z_AI_API_KEY")
            if not zai_key:
                return {
                    "success": False,
                    "error": "Z.AI API authentication failed. Please check your API key configuration. Note: This uses Z.AI's normal API, not the Coding Plan.",
                    "provider": "Z.AI",
                }

            # Prepare the grading prompt with marking scheme if provided
            if marking_scheme_content:
                enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
            else:
                enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

            headers = {
                "Authorization": f"Bearer {zai_key}",
                "Content-Type": "application/json",
                "Accept-Language": "en-US,en",
            }

            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria.",
                    },
                    {"role": "user", "content": enhanced_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            }

            response = requests.post(
                "https://api.z.ai/api/paas/v4/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "grade": data["choices"][0]["message"]["content"],
                    "model": model,
                    "provider": "Z.AI",
                    "usage": {
                        "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                        "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                        "total_tokens": data.get("usage", {}).get("total_tokens", 0),
                    },
                }
            else:
                return {
                    "success": False,
                    "error": f"Z.AI API error: {response.status_code} - {response.text}",
                    "provider": "Z.AI",
                }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Z.AI API connection error: {str(e)}",
                "provider": "Z.AI",
            }
        except Exception as e:
            error_msg = str(e)
            if "auth" in error_msg.lower() or "key" in error_msg.lower():
                return {
                    "success": False,
                    "error": "Z.AI API authentication failed. Please check your API key. Note: This uses Z.AI's normal API, not the Coding Plan.",
                    "provider": "Z.AI",
                }
            else:
                return {
                    "success": False,
                    "error": f"Unexpected error with Z.AI API: {error_msg}",
                    "provider": "Z.AI",
                }


class NanoGPTLLMProvider(LLMProvider):
    """LLM Provider for NanoGPT platform."""

    def get_available_models(self):
        """Fetch available models from NanoGPT API."""
        try:
            nano_key = os.getenv("NANOGPT_API_KEY")
            if not nano_key:
                return {"success": False, "error": "API key not configured"}

            headers = {
                "Authorization": f"Bearer {nano_key}",
                "Content-Type": "application/json",
            }

            response = requests.get(
                "https://nano-gpt.com/api/v1/models",
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                models_data = response.json()
                models = []
                for model in models_data.get("data", []):
                    models.append({
                        "id": model["id"],
                        "name": model.get("name", model["id"]),
                        "description": model.get("description", ""),
                        "context_length": model.get("max_tokens", 0),
                        "provider": "NanoGPT"
                    })
                return {"success": True, "models": models}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def grade_document(
        self,
        text,
        prompt,
        model="chatgpt-4o-latest",
        marking_scheme_content=None,
        temperature=0.3,
        max_tokens=2000,
    ):
        try:
            nano_key = os.getenv("NANOGPT_API_KEY")
            if not nano_key:
                return {
                    "success": False,
                    "error": "NanoGPT API authentication failed. Please check your API key configuration.",
                    "provider": "NanoGPT",
                }

            # Prepare the grading prompt with marking scheme if provided
            if marking_scheme_content:
                enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
            else:
                enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

            headers = {
                "Authorization": f"Bearer {nano_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria.",
                    },
                    {"role": "user", "content": enhanced_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            response = requests.post(
                "https://nano-gpt.com/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "grade": data["choices"][0]["message"]["content"],
                    "model": model,
                    "provider": "NanoGPT",
                    "usage": {
                        "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                        "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                        "total_tokens": data.get("usage", {}).get("total_tokens", 0),
                    },
                }
            else:
                return {
                    "success": False,
                    "error": f"NanoGPT API error: {response.status_code} - {response.text}",
                    "provider": "NanoGPT",
                }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"NanoGPT API connection error: {str(e)}",
                "provider": "NanoGPT",
            }
        except Exception as e:
            error_msg = str(e)
            if "auth" in error_msg.lower() or "key" in error_msg.lower():
                return {
                    "success": False,
                    "error": "NanoGPT API authentication failed. Please check your API key.",
                    "provider": "NanoGPT",
                }
            else:
                return {
                    "success": False,
                    "error": f"Unexpected error with NanoGPT API: {error_msg}",
                    "provider": "NanoGPT",
                }


def get_llm_provider(provider_name):
    """Factory function to get an LLM provider instance."""
    if provider_name == "OpenRouter":
        return OpenRouterLLMProvider()
    elif provider_name == "Claude":
        return ClaudeLLMProvider()
    elif provider_name == "LM Studio":
        return LMStudioLLMProvider()
    elif provider_name == "Ollama":
        return OllamaLLMProvider()
    elif provider_name == "Gemini":
        return GeminiLLMProvider()
    elif provider_name == "OpenAI":
        return OpenAILLMProvider()
    elif provider_name == "Chutes":
        return ChutesLLMProvider()
    elif provider_name == "Z.AI":
        return ZAILLMProvider()
    elif provider_name == "Z.AI Coding Plan":
        return ZAICodingPlanLLMProvider()
    elif provider_name == "NanoGPT":
        return NanoGPTLLMProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")
