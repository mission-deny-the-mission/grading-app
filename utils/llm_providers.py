"""
LLM Provider utilities for grading documents.
This module consolidates all LLM provider logic to eliminate redundancy.
"""
import os
import requests
import openai
from anthropic import Anthropic


def grade_with_openrouter(text, prompt, model="anthropic/claude-3-5-sonnet-20241022", marking_scheme_content=None, temperature=0.3, max_tokens=2000):
    """Grade document using OpenRouter API."""
    try:
        # Re-check environment each call to satisfy tests that clear env
        openrouter_key = os.getenv('OPENROUTER_API_KEY')
        if not openrouter_key:
            return {
                'success': False,
                'error': "OpenRouter API authentication failed. Please check your API key configuration.",
                'provider': 'OpenRouter'
            }
        
        # Configure OpenAI for OpenRouter
        openai.api_key = openrouter_key
        openai.api_base = "https://openrouter.ai/api/v1"

        # Prepare the grading prompt with marking scheme if provided
        if marking_scheme_content:
            enhanced_prompt = f"{prompt}\n\nMarking Scheme:\n{marking_scheme_content}\n\nPlease use the above marking scheme to grade the following document:\n{text}"
        else:
            enhanced_prompt = f"{prompt}\n\nDocument to grade:\n{text}"

        response = openai.ChatCompletion.create(
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
            'provider': 'OpenRouter',
            'usage': response.usage
        }
    except openai.error.AuthenticationError:
        return {
            'success': False,
            'error': "OpenRouter API authentication failed. Please check your API key.",
            'provider': 'OpenRouter'
        }
    except openai.error.RateLimitError:
        return {
            'success': False,
            'error': "OpenRouter API rate limit exceeded. Please try again later.",
            'provider': 'OpenRouter'
        }
    except openai.error.APIError as e:
        return {
            'success': False,
            'error': f"OpenRouter API error: {str(e)}",
            'provider': 'OpenRouter'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Unexpected error with OpenRouter API: {str(e)}",
            'provider': 'OpenRouter'
        }


def grade_with_claude(text, prompt, marking_scheme_content=None, temperature=0.3, max_tokens=2000):
    """Grade document using Claude API."""
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
            model="claude-3-5-sonnet-20241022",
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
            'model': 'claude-3-5-sonnet-20241022',
            'provider': 'Claude',
            'usage': response.usage.dict() if response.usage else None
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


def grade_with_lm_studio(text, prompt, marking_scheme_content=None, temperature=0.3, max_tokens=2000):
    """Grade document using LM Studio API."""
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