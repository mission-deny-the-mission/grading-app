# Saved Configurations Feature

This feature allows users to save and reuse prompts and marking schemes for future grading jobs, improving efficiency and consistency across assignments.

## Features

### Saved Prompts
- **Save Custom Prompts**: Save frequently used grading instructions with metadata
- **Categorization**: Organize prompts by category (e.g., essay, report, assignment)
- **Usage Tracking**: Track how many times each prompt has been used
- **Provider/Model Association**: Link prompts to specific AI providers and models
- **Edit & Delete**: Manage saved prompts through the web interface

### Saved Marking Schemes
- **Save Rubrics**: Save marking schemes and rubrics for reuse
- **File Support**: Supports .docx, .pdf, and .txt files
- **Content Extraction**: Automatically extracts and stores text content
- **Usage Tracking**: Track how many times each marking scheme has been used
- **Edit & Delete**: Manage saved marking schemes through the web interface

## Database Schema

### SavedPrompt Table
```sql
CREATE TABLE saved_prompts (
    id VARCHAR(36) PRIMARY KEY,
    created_at DATETIME,
    updated_at DATETIME,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    prompt_text TEXT NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100),
    usage_count INTEGER DEFAULT 0,
    last_used DATETIME
);
```

### SavedMarkingScheme Table
```sql
CREATE TABLE saved_marking_schemes (
    id VARCHAR(36) PRIMARY KEY,
    created_at DATETIME,
    updated_at DATETIME,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size INTEGER,
    file_type VARCHAR(10),
    content TEXT,
    usage_count INTEGER DEFAULT 0,
    last_used DATETIME
);
```

### Updated GradingJob Table
```sql
ALTER TABLE grading_jobs ADD COLUMN saved_prompt_id VARCHAR(36);
ALTER TABLE grading_jobs ADD COLUMN saved_marking_scheme_id VARCHAR(36);
```

## API Endpoints

### Saved Prompts
- `GET /api/saved-prompts` - Get all saved prompts
- `POST /api/saved-prompts` - Create a new saved prompt
- `GET /api/saved-prompts/<id>` - Get a specific saved prompt
- `PUT /api/saved-prompts/<id>` - Update a saved prompt
- `DELETE /api/saved-prompts/<id>` - Delete a saved prompt

### Saved Marking Schemes
- `GET /api/saved-marking-schemes` - Get all saved marking schemes
- `POST /api/saved-marking-schemes` - Create a new saved marking scheme
- `GET /api/saved-marking-schemes/<id>` - Get a specific saved marking scheme
- `PUT /api/saved-marking-schemes/<id>` - Update a saved marking scheme
- `DELETE /api/saved-marking-schemes/<id>` - Delete a saved marking scheme

## Usage

### Web Interface
1. **Access Saved Configurations**: Navigate to "Saved Configurations" in the main menu
2. **Save a Prompt**: Click "Save Prompt" and fill in the details
3. **Save a Marking Scheme**: Click "Save Marking Scheme" and upload a file
4. **Load Saved Configurations**: Use the "Load Saved Prompt" and "Load Saved Scheme" buttons in the bulk upload form

### Bulk Upload Integration
- **Load Saved Prompt**: Automatically populates the prompt field and provider/model settings
- **Load Saved Marking Scheme**: Shows a preview of the marking scheme content
- **Save Current Configurations**: Save prompts and marking schemes directly from the bulk upload form

### Job Creation
When creating a job, you can now reference saved configurations:
```json
{
    "job_name": "Essay Grading",
    "provider": "openrouter",
    "prompt": "Custom prompt text...",
    "saved_prompt_id": "uuid-of-saved-prompt",
    "saved_marking_scheme_id": "uuid-of-saved-scheme"
}
```

## Benefits

### Efficiency
- **Time Savings**: No need to recreate prompts and marking schemes for similar assignments
- **Consistency**: Ensure consistent grading criteria across multiple jobs
- **Standardization**: Maintain standard prompts and rubrics across courses

### Organization
- **Categorization**: Organize configurations by assignment type or course
- **Usage Tracking**: Identify most-used configurations for optimization
- **Version Control**: Track when configurations were last used and updated

### Quality Assurance
- **Best Practices**: Save and reuse proven grading approaches
- **Collaboration**: Share effective prompts and marking schemes across instructors
- **Audit Trail**: Track which configurations were used for each job

## Migration

To add this feature to an existing installation:

1. **Run Migration Script**:
   ```bash
   python migrate_saved_configurations.py
   ```

2. **Restart Application**: The new features will be available immediately

3. **Database Backup**: Consider backing up your database before migration

## Future Enhancements

### Planned Features
- **Template Library**: Pre-built templates for common assignment types
- **Import/Export**: Share configurations between installations
- **Version History**: Track changes to saved configurations
- **Collaborative Sharing**: Share configurations between users
- **Advanced Search**: Search configurations by content, category, or usage

### Integration Opportunities
- **LMS Integration**: Import configurations from Learning Management Systems
- **API Access**: External applications can manage configurations
- **Bulk Operations**: Import/export multiple configurations at once
- **Analytics**: Detailed usage analytics and recommendations

## Technical Notes

### File Storage
- Marking scheme files are stored in the uploads directory
- File names are timestamped to prevent conflicts
- Original filenames are preserved for display

### Performance
- Usage tracking is updated asynchronously
- Large marking scheme files are processed efficiently
- Database queries are optimized for common operations

### Security
- File uploads are validated for type and size
- User input is sanitized to prevent injection attacks
- Access control can be implemented for multi-user environments
