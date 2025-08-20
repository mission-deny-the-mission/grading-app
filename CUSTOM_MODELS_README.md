# Custom Model Support

This document describes the new custom model functionality that allows users to specify any model name instead of being limited to predefined options.

## Overview

The grading system now supports:
- **Dynamic model selection**: Choose from popular models or enter any custom model name
- **Latest model versions**: Updated defaults to include GPT-5, Claude 4, and other latest models
- **Multi-model comparison**: Compare results from multiple models including custom ones
- **Flexible provider support**: Works with OpenRouter, Claude API, and LM Studio

## Available Models

### OpenRouter Models
The system now includes the latest models available through OpenRouter:

- **Claude 3.5 Sonnet (Latest)** - `anthropic/claude-3-5-sonnet-20241022`
- **GPT-4o** - `openai/gpt-4o`
- **GPT-4o Mini** - `openai/gpt-4o-mini`
- **Claude 3 Opus** - `anthropic/claude-3-opus-20240229`
- **Llama 3.1 70B** - `meta-llama/llama-3.1-70b-instruct`
- **Gemini Pro 1.5** - `google/gemini-pro-1.5`
- **Mistral 7B** - `mistralai/mistral-7b-instruct`
- **GPT-4 Turbo** - `openai/gpt-4-turbo`
- **Claude 3 Haiku** - `anthropic/claude-3-haiku-20240307`

### Claude API Models
Direct Claude API models:

- **Claude 3.5 Sonnet (Latest)** - `claude-3-5-sonnet-20241022`
- **Claude 3 Opus** - `claude-3-opus-20240229`
- **Claude 3 Sonnet** - `claude-3-sonnet-20240229`
- **Claude 3 Haiku** - `claude-3-haiku-20240307`

### LM Studio Models
Local models for LM Studio:

- **Local Model** - `local-model`
- **Llama 3.1 70B** - `llama-3.1-70b-instruct`
- **Mistral 7B** - `mistral-7b-instruct`
- **Code Llama 34B** - `codellama-34b-instruct`

## How to Use Custom Models

### Single File Upload

1. **Select Provider**: Choose your preferred AI provider (OpenRouter, Claude API, or LM Studio)

2. **Enter Custom Model**: 
   - Leave blank to use the default model for the provider
   - Or enter any model name supported by your provider
   - Examples: `openai/gpt-5`, `anthropic/claude-4`, `google/gemini-ultra`

3. **Multi-Model Comparison**:
   - Check "Enable multi-model comparison"
   - Select from popular models or enter custom model names
   - You can mix popular models with custom ones

### Bulk Upload

1. **Job Configuration**:
   - Set provider and optional custom model
   - Enable multi-model comparison if desired
   - Select popular models or enter custom model names

2. **File Upload**:
   - Upload multiple files
   - All files will be processed with the specified models

## API Endpoints

### Get Available Models
```http
GET /api/models
```
Returns all available models for each provider.

### Get Provider Models
```http
GET /api/models/{provider}
```
Returns available models for a specific provider.

### Upload with Custom Model
```http
POST /upload
Content-Type: multipart/form-data

file: [file]
provider: openrouter
customModel: openai/gpt-5
prompt: [grading instructions]
```

### Multi-Model Comparison
```http
POST /upload
Content-Type: multipart/form-data

file: [file]
provider: openrouter
models_to_compare[]: anthropic/claude-3-5-sonnet-20241022
models_to_compare[]: openai/gpt-4o
customModels[]: openai/gpt-5
customModels[]: anthropic/claude-4
prompt: [grading instructions]
```

## Configuration

### Environment Variables
The system uses the same API keys as before:
- `OPENROUTER_API_KEY` - For OpenRouter models
- `CLAUDE_API_KEY` - For Claude API models
- `LM_STUDIO_URL` - For LM Studio models

### Default Models
Default models are defined in `app.py` in the `DEFAULT_MODELS` dictionary. You can modify this to add new models or change defaults.

## Testing

Run the test script to verify custom model functionality:

```bash
python test_custom_models.py
```

This will test:
- Available models API endpoints
- Custom model upload functionality
- Multi-model comparison

## Examples

### Using GPT-5
```javascript
// Single model
const formData = new FormData();
formData.append('file', file);
formData.append('provider', 'openrouter');
formData.append('customModel', 'openai/gpt-5');
formData.append('prompt', 'Grade this document...');
```

### Comparing Multiple Models
```javascript
// Multiple models including custom ones
const formData = new FormData();
formData.append('file', file);
formData.append('provider', 'openrouter');
formData.append('models_to_compare[]', 'anthropic/claude-3-5-sonnet-20241022');
formData.append('models_to_compare[]', 'openai/gpt-4o');
formData.append('customModels[]', 'openai/gpt-5');
formData.append('customModels[]', 'anthropic/claude-4');
formData.append('prompt', 'Grade this document...');
```

## Backward Compatibility

The system maintains full backward compatibility:
- Existing jobs continue to work
- Default models are used when no custom model is specified
- Legacy model names are automatically updated to latest versions

## Troubleshooting

### Model Not Found
If a custom model name is not recognized:
1. Check the model name spelling
2. Verify the model is available through your provider
3. Check provider documentation for correct model identifiers

### API Errors
Common issues:
- **Authentication**: Verify API keys are correctly configured
- **Rate Limits**: Some models may have usage limits
- **Model Availability**: Not all models are available in all regions

### Performance
- Larger models may take longer to process
- Consider using smaller models for faster results
- Multi-model comparison will take proportionally longer

## Future Enhancements

Planned improvements:
- Model performance metrics
- Cost estimation for different models
- Automatic model selection based on document type
- Model recommendation system
