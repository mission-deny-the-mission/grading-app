# Configurable Model Parameters

This document describes the implementation of configurable temperature and maximum output length parameters for the grading system.

## Overview

The grading system now supports configurable parameters for AI model responses:
- **Temperature**: Controls randomness in AI responses (0.0 = focused, 2.0 = creative)
- **Maximum Output Length**: Controls the maximum number of tokens in AI responses (100-8000)

## Implementation Details

### Database Changes

#### New Fields Added
- `temperature` (Float, default: 0.3) - Added to `grading_jobs` and `job_batches` tables
- `max_tokens` (Integer, default: 2000) - Added to `grading_jobs` and `job_batches` tables

#### Migration
- Migration script: `add_model_params_migration.py`
- Run with: `python add_model_params_migration.py`
- Adds new columns with default values to existing tables

### Backend Changes

#### Updated Functions
All grading functions now accept configurable parameters:

1. **`grade_with_openrouter()`** in `tasks.py` and `app.py`
   ```python
   def grade_with_openrouter(text, prompt, model, marking_scheme_content=None, 
                           temperature=0.3, max_tokens=2000)
   ```

2. **`grade_with_claude()`** in `tasks.py` and `app.py`
   ```python
   def grade_with_claude(text, prompt, marking_scheme_content=None, 
                        temperature=0.3, max_tokens=2000)
   ```

3. **`grade_with_lm_studio()`** in `tasks.py` and `app.py`
   ```python
   def grade_with_lm_studio(text, prompt, marking_scheme_content=None, 
                           temperature=0.3, max_tokens=2000)
   ```

#### Job Creation
- Updated job creation API to accept and store temperature and max_tokens
- Parameters are passed from UI forms to backend functions
- Default values applied if not specified

### Frontend Changes

#### UI Controls Added
1. **Single Document Upload** (`index.html`)
   - Temperature slider (0.0 - 2.0, step 0.1)
   - Max tokens input field (100-8000, step 100)
   - Real-time temperature value display

2. **Bulk Upload** (`bulk_upload.html`)
   - Same controls as single upload
   - Parameters stored with job configuration

#### JavaScript Functions
- `updateTemperatureValue(value)` - Updates temperature display
- Form submission includes parameter values
- Reset functions restore default values

## Usage

### Temperature Settings
- **0.0-0.3**: Focused, consistent responses (recommended for grading)
- **0.4-0.7**: Balanced creativity and consistency
- **0.8-1.0**: More creative, varied responses
- **1.1-2.0**: Highly creative, less predictable

### Max Tokens Settings
- **100-500**: Brief responses
- **1000-2000**: Standard grading feedback (default)
- **3000-5000**: Detailed analysis
- **6000-8000**: Comprehensive evaluation

### Example Usage

#### Single Document Upload
1. Select document and marking scheme
2. Choose AI provider and model
3. Adjust temperature slider (e.g., 0.2 for focused grading)
4. Set max tokens (e.g., 3000 for detailed feedback)
5. Enter grading instructions
6. Submit for grading

#### Bulk Upload
1. Configure job with temperature and max_tokens
2. Upload multiple documents
3. All documents processed with same parameters
4. Monitor progress in jobs page

## Testing

### Test Script
Run the test script to verify functionality:
```bash
python test_configurable_params.py
```

### Test Coverage
- Database field accessibility
- Function parameter passing
- Different temperature/token combinations
- All AI providers (OpenRouter, Claude, LM Studio)

## Backward Compatibility

- Existing jobs without parameters use default values (0.3 temperature, 2000 max_tokens)
- All existing functionality preserved
- Migration script handles database updates safely

## Configuration

### Default Values
- Temperature: 0.3 (focused responses)
- Max Tokens: 2000 (standard length)

### Environment Variables
No new environment variables required. Parameters are stored per job.

## Files Modified

### Core Files
- `models.py` - Added database fields
- `tasks.py` - Updated grading functions
- `app.py` - Updated grading functions and job creation

### Templates
- `templates/index.html` - Added UI controls
- `templates/bulk_upload.html` - Added UI controls

### Migration
- `add_model_params_migration.py` - Database migration script
- `test_configurable_params.py` - Test script

## Future Enhancements

Potential improvements:
- Per-model default parameters
- Parameter presets (e.g., "Academic", "Creative", "Technical")
- Parameter validation and constraints
- Parameter usage analytics
- A/B testing with different parameters

## Troubleshooting

### Common Issues
1. **Migration fails**: Check database permissions and connection
2. **Parameters not applied**: Verify form submission includes parameter values
3. **API errors**: Check if AI provider supports specified parameters

### Debug Commands
```bash
# Test database fields
python -c "from app import app; from models import db, GradingJob; app.app_context().push(); job = GradingJob.query.first(); print(f'Temperature: {job.temperature}, Max Tokens: {job.max_tokens}')"

# Test grading functions
python test_configurable_params.py
```
