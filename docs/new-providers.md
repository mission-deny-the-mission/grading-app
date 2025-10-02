# New LLM Providers Documentation

This document describes the three new LLM providers added to the grading application: Chutes AI, Z.AI, and NanoGPT.

## Overview

The grading application now supports 9 LLM providers total:
- **Existing**: OpenRouter, Claude, LM Studio, Ollama, Gemini, OpenAI
- **New**: Chutes AI, Z.AI (Normal API), Z.AI Coding Plan, NanoGPT

## ⚠️ Important Note About Z.AI

Z.AI offers **two different ways to access their models**:

### 1. Z.AI Coding Plan (Subscription)
- **For use within**: Specific coding tools (Claude Code, Cline, Roo Code, etc.)
- **Billing**: Monthly subscription ($3-$150/month) with usage quotas
- **Restriction**: **Cannot be accessed via API calls**
- **Use Case**: AI-assisted coding within supported IDEs/editors

### 2. Z.AI Normal API (Pay-per-use)
- **For use within**: General applications and API integrations
- **Billing**: Pay-per-token (separate from Coding Plan)
- **Access**: Available via standard REST API
- **Use Case**: **This grading application uses this method**

**This integration uses Z.AI's Normal API only** - it does not use or affect your Coding Plan subscription.

## Provider Details

### 1. Chutes AI

**Provider Name**: `Chutes`  
**Default Model**: `microsoft/DialoGPT-medium`  
**API Endpoint**: `https://api.chutes.ai/v1/chat/completions`  
**Models Endpoint**: `https://api.chutes.ai/v1/models`  
**Environment Variable**: `CHUTES_API_KEY`

#### Features
- OpenAI-compatible API endpoint
- Support for custom HuggingFace models via VLLM template
- Streaming support
- Automatic model downloading and caching
- High-performance inference with PagedAttention

#### Usage Example
```python
from utils.llm_providers import get_llm_provider

provider = get_llm_provider("Chutes")
result = provider.grade_document(
    text="Document content",
    prompt="Grade this document",
    model="microsoft/DialoGPT-medium",
    temperature=0.3,
    max_tokens=2000
)
```

#### Configuration
Add to your `.env` file:
```env
CHUTES_API_KEY=your-chutes-api-key-here
```

---

### 2. Z.AI (Normal API)

**Provider Name**: `Z.AI`  
**Default Model**: `glm-4.6`  
**API Endpoint**: `https://api.z.ai/api/paas/v4/chat/completions`  
**Environment Variable**: `Z_AI_API_KEY`

#### ⚠️ Critical: This Uses Z.AI Normal API, NOT Coding Plan

This integration works **exclusively** with Z.AI's Normal API and **cannot** use Coding Plan subscriptions.

| Feature | Z.AI Coding Plan | Z.AI Normal API (This Integration) |
|---------|------------------|-------------------------------------|
| **Access Method** | Within coding tools only | Standard REST API calls |
| **Billing** | Monthly subscription | Pay-per-token |
| **Usage Limits** | Quota-based (120-2400 prompts/5hrs) | No preset limits |
| **Available Models** | GLM-4.5, GLM-4.5-Air | All GLM models |
| **Use Case** | AI-assisted coding | General applications |
| **API Access** | ❌ Not available | ✅ Full API access |

#### Available Models (API Access)
- `glm-4.6` - Latest flagship model series for agent applications
- `glm-4.5` - Foundation model for intelligent agents
- `glm-4.5-air` - Lightweight version of GLM-4.5
- `glm-4.5-x` - Enhanced version of GLM-4.5
- `glm-4.5-airx` - Enhanced lightweight version
- `glm-4.5-flash` - Fast response model
- `glm-4-32b-0414-128k` - Cost-effective model with 128K context

#### Features
- Multimodal inputs (text, images, audio, video, files)
- Configurable parameters (temperature, max tokens, tool use)
- Streaming and non-streaming output modes
- Built-in web search capabilities
- Chain of thought reasoning for GLM-4.5 and above

#### Usage Example
```python
from utils.llm_providers import get_llm_provider

provider = get_llm_provider("Z.AI")
result = provider.grade_document(
    text="Document content", 
    prompt="Grade this document",
    model="glm-4.6",
    temperature=0.3,
    max_tokens=2000
)
```

#### Configuration
Add to your `.env` file:
```env
Z_AI_API_KEY=your-z-ai-api-key-here
```

**Note**: This API key is for Z.AI's normal API, not the Coding Plan subscription.

---

### 3. Z.AI Coding Plan (Subscription)

**Provider Name**: `Z.AI Coding Plan`  
**Default Model**: `glm-4.6`  
**API Endpoint**: `https://api.z.ai/api/anthropic/v1/messages`  
**Environment Variable**: `Z_AI_CODING_PLAN_API_KEY`

#### ⚠️ Requires Active Subscription
This provider requires an active Z.AI Coding Plan subscription and works through an Anthropic API-compatible endpoint.

#### Available Models (Coding Plan)
- `glm-4.6` - Latest flagship model for coding (Coding Plan)
- `glm-4.5` - Foundation model for coding (Coding Plan)
- `glm-4.5-air` - Lightweight model for auxiliary tasks (Coding Plan)

#### Features
- Uses subscription quota instead of pay-per-token
- Anthropic API-compatible endpoint
- Limited model selection (optimized for coding)
- Lower cost per usage compared to normal API
- Quota-based usage limits (120-2400 prompts per 5 hours)

#### Usage Example
```python
from utils.llm_providers import get_llm_provider

provider = get_llm_provider("Z.AI Coding Plan")
result = provider.grade_document(
    text="Document content",
    prompt="Grade this document",
    model="glm-4.6",
    temperature=0.3,
    max_tokens=2000
)
```

#### Configuration
Add to your `.env` file:
```env
Z_AI_CODING_PLAN_API_KEY=your-z-ai-coding-plan-key-here
```

**Note**: This API key is for Z.AI's Coding Plan and requires an active subscription.

---

### 4. NanoGPT

**Provider Name**: `NanoGPT`  
**Default Model**: `chatgpt-4o-latest`  
**API Endpoint**: `https://nano-gpt.com/api/v1/chat/completions`  
**Models Endpoint**: `https://nano-gpt.com/api/v1/models`  
**Environment Variable**: `NANOGPT_API_KEY`

#### Features
- Access to 602+ models (451 text, 78 image, 34 video, 10 audio, 26 embedding)
- OpenAI-compatible API
- Streaming support
- Multiple model providers (OpenAI, Anthropic, Google, etc.)
- Pay-as-you-go pricing with no monthly fees

#### Model Categories
- **Text Models**: GPT-4 variants, Claude, Gemini, Llama, and more
- **Image Models**: DALL-E, Midjourney, Flux, Stable Diffusion
- **Video Models**: Kling, Veo, Hunyuan, MiniMax
- **Audio Models**: ElevenLabs, OpenAI TTS, Whisper
- **Embedding Models**: OpenAI, Google, Jina, BAAI

#### Usage Example
```python
from utils.llm_providers import get_llm_provider

provider = get_llm_provider("NanoGPT")
result = provider.grade_document(
    text="Document content",
    prompt="Grade this document", 
    model="chatgpt-4o-latest",
    temperature=0.3,
    max_tokens=2000
)
```

#### Configuration
Add to your `.env` file:
```env
NANOGPT_API_KEY=your-nanogpt-api-key-here
```

---

## Integration Details

### Provider Classification
All three new providers are classified as **proprietary providers**, meaning they:
- Require API keys for authentication
- Have rate limiting applied (default: 4 concurrent requests)
- Are included in the `_PROPRIETARY_PROVIDERS` set

### Concurrency Limits
You can configure concurrency limits for each provider using environment variables:

```env
PROVIDER_MAX_CHUTES=6
PROVIDER_MAX_Z_AI=4  
PROVIDER_MAX_NANOGPT=8
```

Or use the JSON format:
```env
PROVIDER_MAX_PARALLEL='{"Chutes": 6, "Z.AI": 4, "NanoGPT": 8}'
```

### Error Handling
All providers implement comprehensive error handling:
- **Authentication errors**: Clear messages about missing/invalid API keys
- **Rate limiting**: Proper error messages when limits are exceeded
- **Network errors**: Connection timeout and retry handling
- **API errors**: Detailed error messages from provider responses

### Response Format
All providers return a consistent response format:
```python
{
    "success": True/False,
    "grade": "graded content" if success else None,
    "model": "model_name_used",
    "provider": "provider_name", 
    "usage": {
        "prompt_tokens": int,
        "completion_tokens": int, 
        "total_tokens": int
    } if success else None,
    "error": "error_message" if not success else None
}
```

## Testing

The new providers include comprehensive test coverage in `tests/test_new_providers.py`:

- **Authentication tests**: Verify proper handling of missing/invalid API keys
- **API integration tests**: Mock successful API calls and responses
- **Error handling tests**: Test network errors, API errors, and edge cases
- **Factory function tests**: Ensure correct provider instantiation

Run tests with:
```bash
python run_tests.py --file tests/test_new_providers.py
```

## Migration Guide

### For Existing Users
1. Add the new environment variables to your `.env` file
2. The new providers will automatically appear in the provider selection UI
3. No code changes required - the providers integrate seamlessly

### For Developers
1. Import the new providers: `from utils.llm_providers import get_llm_provider`
2. Use the factory function: `provider = get_llm_provider("Chutes")`
3. Call the standard interface: `provider.grade_document(...)`

## API Key Setup

### Chutes AI
1. Visit https://chutes.ai
2. Create an account and navigate to the dashboard
3. Generate an API key from the API management section
4. Add to `.env`: `CHUTES_API_KEY=your_key_here`

### Z.AI (Normal API)
1. Visit https://docs.z.ai
2. Register or login to the Z.AI Open Platform
3. Navigate to API Keys management
4. Create and copy your API key for **normal API usage** (not Coding Plan)
5. Add to `.env`: `Z_AI_API_KEY=your_key_here`

**⚠️ Important**: This API key is for Z.AI's normal API only and is billed per token.

### Z.AI Coding Plan
1. Visit https://docs.z.ai/devpack/overview
2. Subscribe to a Coding Plan (Lite: $3/mo, Pro: $15/mo, Max: $150/mo)
3. Get your API key from the Z.AI platform
4. Add to `.env`: `Z_AI_CODING_PLAN_API_KEY=your_key_here`

**⚠️ Important**: This requires an active Z.AI Coding Plan subscription and uses your subscription quota.

### NanoGPT
1. Visit https://nano-gpt.com
2. Create an account
3. Generate API keys from the API Keys section
4. Add to `.env`: `NANOGPT_API_KEY=your_key_here`

## Troubleshooting

### Common Issues

**"API key not configured"**
- Ensure the correct environment variable is set in `.env`
- Restart the application after adding environment variables

**"Authentication failed"** 
- Verify API key is valid and not expired
- Check for typos in the API key
- Ensure API key has proper permissions
- **Z.AI Specific**: Make sure you're using normal API key, not Coding Plan credentials

**"Connection error"**
- Check internet connectivity
- Verify API endpoints are accessible
- Check firewall/proxy settings

**Rate limiting**
- Reduce concurrency limits in environment variables
- Implement retry logic in your application
- Consider upgrading your API plan

**Z.AI Specific Issues**
- **Normal API**: "I have a Coding Plan but it's not working" - Use Z.AI (Normal API) provider instead
- **Normal API**: "Unexpected charges" - This integration uses normal API billing, separate from Coding Plan
- **Normal API**: "Model not available" - Ensure you're using API-supported models

**Z.AI Coding Plan Specific Issues**
- **"Coding Plan not working"**: Ensure you have an active subscription and correct API key
- **"Quota exceeded"**: Wait for the next 5-hour cycle or upgrade your plan
- **"Model not supported"**: Coding Plan only supports glm-4.6, glm-4.5, and glm-4.5-air
- **"Authentication failed"**: Verify your Coding Plan subscription and API key

### Debug Tips
1. Check application logs for detailed error messages
2. Test API keys with curl commands first
3. Use the test files to verify provider functionality
4. Monitor usage in the provider dashboards
5. **Z.AI Specific**: 
   - Normal API: Check your Z.AI API billing dashboard
   - Coding Plan: Check your subscription usage and quota status

## Performance Considerations

### Chutes AI
- Best for custom HuggingFace model deployment
- High performance with VLLM optimization
- Consider GPU requirements for larger models

### Z.AI
- Excellent for Chinese language processing
- Strong reasoning capabilities with GLM-4.6
- Good balance of performance and cost
- **⚠️ Billing**: Uses normal API (pay-per-token), NOT Coding Plan quotas
- **Best for**: General text processing, multilingual tasks, structured grading
- **Not for**: Coding Plan subscribers expecting free usage (requires separate API billing)

### Z.AI Coding Plan
- **⚠️ Billing**: Uses subscription quota, NOT per-token billing
- **Best for**: Coding Plan subscribers looking for cost-effective grading
- **Perfect for**: Users who already have Coding Plan subscriptions
- **Restrictions**: Limited model selection and quota-based usage

### NanoGPT
- Largest model selection (600+ models)
- Flexible pricing with pay-as-you-go
- Good for experimenting with different models

## Future Enhancements

Potential improvements for the new providers:
1. **Streaming support**: Implement real-time response streaming
2. **Model caching**: Cache model lists to reduce API calls
3. **Advanced features**: Implement provider-specific features (web search, multimodal)
4. **Monitoring**: Add detailed metrics and monitoring
5. **Batch processing**: Optimize for batch grading operations

## Support

For provider-specific issues:
- **Chutes AI**: https://chutes.ai/docs
- **Z.AI**: https://docs.z.ai
- **NanoGPT**: https://nano-gpt.com/api

For application integration issues, check the application logs or create an issue in the project repository.