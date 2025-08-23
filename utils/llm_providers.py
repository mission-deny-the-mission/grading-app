"""
LLM Provider utilities for grading documents.
This module consolidates all LLM provider logic to eliminate redundancy.
"""
import os
import requests
import openai
from anthropic import Anthropic
import google.generativeai as genai
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract Base Class for LLM Providers."""

    @abstractmethod
    def grade_document(self, text, prompt, marking_scheme_content=None, temperature=0.3, max_tokens=2000):
        """
        Abstract method to grade a document using the LLM provider.
        Implementations should handle API calls, error handling, and response parsing.
        """
        pass


class OpenRouterLLMProvider(LLMProvider):
    """LLM Provider for OpenRouter API."""

    def grade_document(self, text, prompt, model="anthropic/claude-opus-4-1", marking_scheme_content=None, temperature=0.3, max_tokens=2000):
        try:
            # Re-check environment each call to satisfy tests that clear env
            openrouter_key = os.getenv('OPENROUTER_API_KEY')
            if not openrouter_key:
                return {
                    'success': False,
                    'error': "OpenRouter API authentication failed. Please check your API key configuration.",
                    'provider': 'OpenRouter'
                }

            # Prepare the grading prompt with marking scheme if provided
            if marking_scheme_content:
                enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
            else:
                enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

            # Use requests library for OpenRouter API to avoid OpenAI SDK compatibility issues
            headers = {
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria."},
                    {"role": "user", "content": enhanced_prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                grade_text = result['choices'][0]['message']['content']
                usage = result.get('usage')
            else:
                response.raise_for_status()

            return {
                'success': True,
                'grade': grade_text,
                'model': model,
                'provider': 'OpenRouter',
                'usage': usage
            }
        except Exception as e:
            error_msg = str(e)
            if 'auth' in error_msg.lower() or 'key' in error_msg.lower():
                return {
                    'success': False,
                    'error': "OpenRouter API authentication failed. Please check your API key.",
                    'provider': 'OpenRouter'
                }
            elif 'rate' in error_msg.lower() and 'limit' in error_msg.lower():
                return {
                    'success': False,
                    'error': "OpenRouter API rate limit exceeded. Please try again later.",
                    'provider': 'OpenRouter'
                }
            else:
                return {
                    'success': False,
                    'error': f"Unexpected error with OpenRouter API: {error_msg}",
                    'provider': 'OpenRouter'
                }


class ClaudeLLMProvider(LLMProvider):
    """LLM Provider for Claude API."""

    def grade_document(self, text, prompt, marking_scheme_content=None, temperature=0.3, max_tokens=2000):
        # Re-check environment each call to satisfy tests that clear env
        claude_key = os.getenv('CLAUDE_API_KEY')
        if not claude_key:
            return {
                'success': False,
                'error': "Claude API not configured or failed to initialize",
                'provider': 'Claude'
            }
        
        # Create client when key is present
        try:
            anthropic = Anthropic(api_key=claude_key)
        except Exception:
            return {
                'success': False,
                'error': "Claude API not configured or failed to initialize",
                'provider': 'Claude'
            }

        try:
            # Prepare the grading prompt with marking scheme if provided
            if marking_scheme_content:
                enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
            else:
                enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

            response = anthropic.messages.create(
                model="claude-4-opus-20250805",
                max_tokens=max_tokens,
                temperature=temperature,
                system="You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria.",
                messages=[
                    {
                        "role": "user",
                        "content": enhanced_prompt
                    }
                ]
            )

            return {
                'success': True,
                'grade': response.content[0].text,
                'model': 'claude-4-opus-20250805',
                'provider': 'Claude',
                'usage': response.usage.model_dump() if response.usage else None
            }
        except Exception as e:
            error_msg = str(e)
            if "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
                return {
                    'success': False,
                    'error': "Claude API authentication failed. Please check your API key.",
                    'provider': 'Claude'
                }
            elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
                return {
                    'success': False,
                    'error': "Claude API rate limit exceeded. Please try again later.",
                    'provider': 'Claude'
                }
            elif "timeout" in error_msg.lower():
                return {
                    'success': False,
                    'error': "Claude API request timed out. Please try again.",
                    'provider': 'Claude'
                }
            else:
                return {
                    'success': False,
                    'error': f"Claude API error: {error_msg}",
                    'provider': 'Claude'
                }


class LMStudioLLMProvider(LLMProvider):
    """LLM Provider for LM Studio API."""

    def grade_document(self, text, prompt, marking_scheme_content=None, temperature=0.3, max_tokens=2000):
        # Get URL from environment variable, don't use cached module-level variable for testing
        lm_studio_url = os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1')
        
        try:
            # Prepare the grading prompt with marking scheme if provided
            if marking_scheme_content:
                enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
            else:
                enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

            response = requests.post(
                f"{lm_studio_url}/chat/completions",
                json={
                    "model": "local-model",
                    "messages": [
                        {"role": "system", "content": "You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria."},
                        {"role": "user", "content": enhanced_prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                headers={"Content-Type": "application/json"},
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'grade': result['choices'][0]['message']['content'],
                    'model': 'local-model',
                    'provider': 'LM Studio',
                    'usage': result.get('usage')
                }
            elif response.status_code == 404:
                return {
                    'success': False,
                    'error': "LM Studio endpoint not found. Please check if LM Studio is running and the URL is correct.",
                    'provider': 'LM Studio'
                }
            elif response.status_code == 500:
                return {
                    'success': False,
                    'error': "LM Studio internal server error. Please check LM Studio logs.",
                    'provider': 'LM Studio'
                }
            else:
                return {
                    'success': False,
                    'error': f"LM Studio API error: {response.status_code} - {response.text}",
                    'provider': 'LM Studio'
                }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': f"Could not connect to LM Studio at {lm_studio_url}. Please check if LM Studio is running.",
                'provider': 'LM Studio'
            }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': "LM Studio request timed out. Please try again.",
                'provider': 'LM Studio'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"LM Studio API error: {str(e)}",
                'provider': 'LM Studio'
            }


class OllamaLLMProvider(LLMProvider):
    """LLM Provider for Ollama API."""

    def grade_document(self, text, prompt, model="llama2", marking_scheme_content=None, temperature=0.3, max_tokens=2000):
        ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate')

        try:
            if marking_scheme_content:
                enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
            else:
                enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"
            
            # Ollama doesn't directly support system messages in the /api/generate endpoint for all models
            # We can prepend the system message to the user prompt for a similar effect
            full_prompt = "You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria.\n\n" + enhanced_prompt

            response = requests.post(
                ollama_url,
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "temperature": temperature,
                    "options": {"num_predict": max_tokens} # Ollama uses num_predict for max_tokens
                },
                headers={"Content-Type": "application/json"},
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                # Ollama's /api/generate streams responses, so we need to concatenate them
                # For a single response, it might be directly in 'response' or 'eval_count' etc.
                # This assumes a non-streaming response for simplicity, or takes the last part
                final_response_content = result.get('response', '')
                
                # In case of streaming, result might not have 'response' directly at top level
                # Let's assume for now a single call returns the full response, or adjust if needed

                return {
                    'success': True,
                    'grade': final_response_content,
                    'model': model,
                    'provider': 'Ollama',
                    'usage': {
                        'prompt_tokens': result.get('prompt_eval_count'),
                        'completion_tokens': result.get('eval_count'),
                        'total_tokens': (result.get('prompt_eval_count', 0) + result.get('eval_count', 0))
                    }
                }
            elif response.status_code == 404:
                return {
                    'success': False,
                    'error': "Ollama endpoint not found. Please check if Ollama is running and the URL is correct.",
                    'provider': 'Ollama'
                }
            elif response.status_code == 500:
                return {
                    'success': False,
                    'error': "Ollama internal server error. Please check Ollama logs.",
                    'provider': 'Ollama'
                }
            else:
                return {
                    'success': False,
                    'error': f"Ollama API error: {response.status_code} - {response.text}",
                    'provider': 'Ollama'
                }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': f"Could not connect to Ollama at {ollama_url}. Please check if Ollama is running.",
                'provider': 'Ollama'
            }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': "Ollama request timed out. Please try again.",
                'provider': 'Ollama'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Ollama API error: {str(e)}",
                'provider': 'Ollama'
            }


class GeminiLLMProvider(LLMProvider):
    """LLM Provider for Google Gemini API."""

    def grade_document(self, text, prompt, model="gemini-2.5-pro", marking_scheme_content=None, temperature=0.3, max_tokens=2000):
        try:
            # Re-check environment each call to satisfy tests that clear env
            gemini_key = os.getenv('GEMINI_API_KEY')
            if not gemini_key:
                return {
                    'success': False,
                    'error': "Gemini API authentication failed. Please check your API key configuration.",
                    'provider': 'Gemini'
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
                system_instruction="You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria."
            )
            
            # Generate response
            response = gemini_model.generate_content(
                enhanced_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )

            return {
                'success': True,
                'grade': response.text,
                'model': model,
                'provider': 'Gemini',
                'usage': {
                    'prompt_tokens': response.usage_metadata.prompt_token_count if response.usage_metadata else None,
                    'completion_tokens': response.usage_metadata.candidates_token_count if response.usage_metadata else None,
                    'total_tokens': response.usage_metadata.total_token_count if response.usage_metadata else None
                }
            }
        except Exception as e:
            error_msg = str(e)
            if "authentication" in error_msg.lower() or "api_key" in error_msg.lower() or "permission" in error_msg.lower():
                return {
                    'success': False,
                    'error': "Gemini API authentication failed. Please check your API key.",
                    'provider': 'Gemini'
                }
            elif "quota" in error_msg.lower() or "rate" in error_msg.lower() or "limit" in error_msg.lower():
                return {
                    'success': False,
                    'error': "Gemini API rate limit exceeded. Please try again later.",
                    'provider': 'Gemini'
                }
            elif "timeout" in error_msg.lower():
                return {
                    'success': False,
                    'error': "Gemini API request timed out. Please try again.",
                    'provider': 'Gemini'
                }
            else:
                return {
                    'success': False,
                    'error': f"Gemini API error: {error_msg}",
                    'provider': 'Gemini'
                }


class OpenAILLMProvider(LLMProvider):
    """LLM Provider for OpenAI API (direct, not through OpenRouter)."""

    def grade_document(self, text, prompt, model="gpt-5", marking_scheme_content=None, temperature=0.3, max_tokens=2000):
        try:
            # Re-check environment each call to satisfy tests that clear env
            openai_key = os.getenv('OPENAI_API_KEY')
            if not openai_key:
                return {
                    'success': False,
                    'error': "OpenAI API authentication failed. Please check your API key configuration.",
                    'provider': 'OpenAI'
                }
            
            # Create OpenAI client with new SDK
            client = openai.OpenAI(api_key=openai_key)
            
            # Prepare the grading prompt with marking scheme if provided
            if marking_scheme_content:
                enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
            else:
                enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a professional document grader. Provide detailed, constructive feedback based on the provided marking scheme and criteria."},
                    {"role": "user", "content": enhanced_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            return {
                'success': True,
                'grade': response.choices[0].message.content,
                'model': model,
                'provider': 'OpenAI',
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
        except openai.AuthenticationError:
            return {
                'success': False,
                'error': "OpenAI API authentication failed. Please check your API key.",
                'provider': 'OpenAI'
            }
        except openai.RateLimitError:
            return {
                'success': False,
                'error': "OpenAI API rate limit exceeded. Please try again later.",
                'provider': 'OpenAI'
            }
        except openai.APIError as e:
            return {
                'success': False,
                'error': f"OpenAI API error: {str(e)}",
                'provider': 'OpenAI'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Unexpected error with OpenAI API: {str(e)}",
                'provider': 'OpenAI'
            }


def get_llm_provider(provider_name):
    """Factory function to get an LLM provider instance."""
    if provider_name == 'OpenRouter':
        return OpenRouterLLMProvider()
    elif provider_name == 'Claude':
        return ClaudeLLMProvider()
    elif provider_name == 'LM Studio':
        return LMStudioLLMProvider()
    elif provider_name == 'Ollama':
        return OllamaLLMProvider()
    elif provider_name == 'Gemini':
        return GeminiLLMProvider()
    elif provider_name == 'OpenAI':
        return OpenAILLMProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")


# Backward compatibility wrapper functions
def grade_with_openrouter(text, prompt, model="anthropic/claude-opus-4-1", marking_scheme_content=None, temperature=0.3, max_tokens=2000):
    """Backward compatibility wrapper for OpenRouter grading."""
    provider = OpenRouterLLMProvider()
    return provider.grade_document(text, prompt, model, marking_scheme_content, temperature, max_tokens)


def grade_with_claude(text, prompt, marking_scheme_content=None, temperature=0.3, max_tokens=2000):
    """Backward compatibility wrapper for Claude grading."""
    provider = ClaudeLLMProvider()
    return provider.grade_document(text, prompt, marking_scheme_content, temperature, max_tokens)


def grade_with_lm_studio(text, prompt, marking_scheme_content=None, temperature=0.3, max_tokens=2000):
    """Backward compatibility wrapper for LM Studio grading."""
    provider = LMStudioLLMProvider()
    return provider.grade_document(text, prompt, marking_scheme_content, temperature, max_tokens)


def grade_with_gemini(text, prompt, model="gemini-2.5-pro", marking_scheme_content=None, temperature=0.3, max_tokens=2000):
    """Backward compatibility wrapper for Gemini grading."""
    provider = GeminiLLMProvider()
    return provider.grade_document(text, prompt, model, marking_scheme_content, temperature, max_tokens)


def grade_with_openai(text, prompt, model="gpt-5", marking_scheme_content=None, temperature=0.3, max_tokens=2000):
    """Backward compatibility wrapper for OpenAI grading."""
    provider = OpenAILLMProvider()
    return provider.grade_document(text, prompt, model, marking_scheme_content, temperature, max_tokens)