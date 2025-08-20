# Multi-Model Comparison Feature

This document describes the new multi-model comparison feature that allows you to grade documents using multiple AI models simultaneously and compare their results.

## Overview

The multi-model comparison feature enables you to:
- Select 2 or more AI models to grade the same document
- Compare grading results side-by-side
- Identify differences in feedback and assessment approaches
- Make more informed decisions based on multiple AI perspectives

## How to Use

### Single Document Upload

1. **Enable Comparison**: Check the "Enable multi-model comparison" checkbox on the main upload page
2. **Select Models**: Choose 2 or more models from the available options:
   - **OpenRouter Models**:
     - Claude 3.5 Sonnet
     - GPT-4o
     - Claude 3 Opus
     - Llama 3.1 70B
   - **Other Models**:
     - Claude Direct API
     - LM Studio (Local)
3. **Upload Document**: Select your document and submit
4. **View Results**: Compare results from all selected models

### Bulk Upload

1. **Create Job**: Configure your grading job as usual
2. **Enable Comparison**: Check the "Enable multi-model comparison" checkbox
3. **Select Models**: Choose the models you want to compare
4. **Upload Files**: Upload multiple documents
5. **Monitor Progress**: Track processing across all models
6. **View Results**: Access comparison results in the job details

## Available Models

### OpenRouter Models
- **Claude 3.5 Sonnet**: Anthropic's latest model, excellent for detailed analysis
- **GPT-4o**: OpenAI's most capable model, great for comprehensive feedback
- **Claude 3 Opus**: Anthropic's most powerful model for complex tasks
- **Llama 3.1 70B**: Meta's open-source model, good for general grading

### Direct API Models
- **Claude Direct API**: Direct access to Claude models via Anthropic API
- **LM Studio**: Local model inference for privacy-sensitive documents

## Database Changes

The feature adds a new `GradeResult` table to store individual results from each model:

```sql
CREATE TABLE grade_results (
    id VARCHAR(36) PRIMARY KEY,
    created_at DATETIME,
    grade TEXT NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'completed',
    error_message TEXT,
    grade_metadata JSON,
    submission_id VARCHAR(36) NOT NULL,
    FOREIGN KEY (submission_id) REFERENCES submissions (id)
);
```

The `GradingJob` table also gets a new `models_to_compare` column to store the list of models for comparison.

## Migration

To enable this feature on existing installations:

1. Run the migration script:
   ```bash
   python migrate_db.py
   ```

2. Restart your application

## API Changes

### Upload Endpoint

The `/upload` endpoint now accepts a `models_to_compare[]` parameter:

```javascript
// Example request
const formData = new FormData();
formData.append('file', file);
formData.append('prompt', prompt);
formData.append('provider', 'openrouter');
formData.append('models_to_compare[]', 'anthropic/claude-3.5-sonnet');
formData.append('models_to_compare[]', 'openai/gpt-4o');
```

### Response Format

For single model (backward compatibility):
```json
{
  "success": true,
  "provider": "OpenRouter",
  "model": "anthropic/claude-3.5-sonnet",
  "grade": "Detailed feedback..."
}
```

For multiple models:
```json
{
  "success": true,
  "comparison": true,
  "results": [
    {
      "success": true,
      "provider": "OpenRouter",
      "model": "anthropic/claude-3.5-sonnet",
      "grade": "Feedback from Claude..."
    },
    {
      "success": true,
      "provider": "OpenRouter", 
      "model": "openai/gpt-4o",
      "grade": "Feedback from GPT-4o..."
    }
  ],
  "total_models": 2,
  "successful_models": 2
}
```

## Job Creation

When creating jobs for bulk processing, include the `models_to_compare` field:

```javascript
const jobData = {
  job_name: "Essay Comparison",
  provider: "openrouter",
  models_to_compare: ["anthropic/claude-3.5-sonnet", "openai/gpt-4o"],
  prompt: "Grade this essay..."
};
```

## Viewing Results

### Job Details Page

The job details page shows:
- Number of models being compared
- Individual results for each submission
- Side-by-side comparison in the submission modal

### Submission Modal

When viewing individual submissions:
- Multiple grade results are displayed in separate cards
- Each result shows the model name and provider
- Failed models show error messages
- Successful results show the full grading feedback

## Best Practices

1. **Model Selection**: Choose models with different strengths:
   - Claude models excel at detailed analysis
   - GPT models are good at comprehensive feedback
   - Llama models offer open-source alternatives

2. **Provider Configuration**: Ensure your API keys are properly configured for all selected providers

3. **Cost Management**: Be aware that using multiple models increases API costs

4. **Processing Time**: Multi-model grading takes longer than single-model grading

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure all required API keys are configured
2. **Model Availability**: Some models may not be available in all regions
3. **Rate Limits**: Multiple models may hit rate limits faster

### Error Handling

- Failed models are clearly marked in the results
- Individual model failures don't affect other models
- Retry functionality works for failed submissions

## Future Enhancements

Potential improvements for the multi-model comparison feature:
- Statistical analysis of grading differences
- Confidence scores for each model
- Automated model selection based on document type
- Export comparison reports
- Model performance tracking over time
