# Marking Scheme Feature

This document describes the new marking scheme functionality that allows users to upload grading rubrics and marking schemes along with documents to be graded.

## Overview

The marking scheme feature enables users to:
- Upload marking schemes/rubrics in various formats (DOCX, PDF, TXT)
- Associate marking schemes with grading jobs
- Use marking schemes to guide AI grading for more consistent and structured feedback
- View marking scheme content and metadata in the job details

## Features

### 1. Marking Scheme Upload
- **Supported Formats**: DOCX, PDF, TXT
- **File Size Limit**: 16MB (same as document uploads)
- **Content Extraction**: Automatically extracts text content from uploaded files
- **Metadata Storage**: Stores filename, size, type, and description

### 2. Integration with Grading Process
- **Enhanced Prompts**: Marking scheme content is automatically included in AI grading prompts
- **Structured Feedback**: AI models use the marking scheme to provide more consistent and structured feedback
- **Multiple Models**: Works with all supported AI providers (OpenRouter, Claude, LM Studio)

### 3. User Interface
- **Upload Interface**: Simple file upload field in both single document and bulk upload forms
- **Job Details**: Display marking scheme information in job detail pages
- **Content Viewer**: Modal popup to view marking scheme content
- **Download**: Ability to download marking scheme content

## Usage

### Single Document Upload
1. Navigate to the main upload page
2. Select your document to grade
3. **Optional**: Upload a marking scheme file
4. Configure your grading settings (provider, model, prompt)
5. Submit for grading

### Bulk Upload
1. Navigate to the bulk upload page
2. Configure your job settings
3. **Optional**: Upload a marking scheme file
4. Create the job
5. Upload multiple documents to the job

### Viewing Marking Schemes
1. Go to a job detail page
2. If a marking scheme was uploaded, it will appear in the right sidebar
3. Click "View Content" to see the full marking scheme
4. Use "Download" to save the marking scheme content

## Technical Implementation

### Database Schema
```sql
-- Marking schemes table
CREATE TABLE marking_schemes (
    id VARCHAR(36) PRIMARY KEY,
    created_at DATETIME,
    updated_at DATETIME,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size INTEGER,
    file_type VARCHAR(10),
    content TEXT
);

-- Updated grading_jobs table
ALTER TABLE grading_jobs ADD COLUMN marking_scheme_id VARCHAR(36) REFERENCES marking_schemes(id);
```

### API Endpoints
- `POST /upload_marking_scheme` - Upload a marking scheme
- `POST /upload` - Upload document with optional marking scheme
- `POST /create_job` - Create job with optional marking scheme
- `POST /upload_bulk` - Bulk upload with job-level marking scheme

### File Processing
- **DOCX**: Uses python-docx library to extract text
- **PDF**: Uses PyPDF2 library to extract text
- **TXT**: Direct text file reading
- **Content Storage**: Extracted text is stored in the database for quick access

### AI Integration
The marking scheme content is automatically included in AI prompts:
```
[User's grading instructions]

Marking Scheme:
[Marking scheme content]

Please use the above marking scheme to grade the following document:
[Document content]
```

## Benefits

1. **Consistency**: Ensures all documents are graded using the same criteria
2. **Structure**: Provides clear grading framework for AI models
3. **Transparency**: Users can see exactly what criteria are being used
4. **Flexibility**: Supports various marking scheme formats and styles
5. **Efficiency**: Reduces the need to manually specify grading criteria for each job

## Example Marking Scheme Format

```
GRADING RUBRIC FOR ESSAYS

CRITERIA:
1. Thesis Statement (20 points)
   - Clear and specific thesis
   - Well-argued position
   - Appropriate scope

2. Content and Analysis (30 points)
   - Relevant evidence and examples
   - Logical argument development
   - Critical thinking demonstrated

3. Organization (20 points)
   - Clear structure and flow
   - Effective transitions
   - Logical paragraph organization

4. Writing Quality (20 points)
   - Clear and concise writing
   - Appropriate tone and style
   - Grammar and mechanics

5. Citations and References (10 points)
   - Proper citation format
   - Adequate source integration
   - Works cited page

GRADING SCALE:
A (90-100): Excellent work that exceeds expectations
B (80-89): Good work that meets most expectations
C (70-79): Satisfactory work with some areas for improvement
D (60-69): Below average work with significant issues
F (0-59): Unsatisfactory work that fails to meet basic requirements
```

## Testing

Run the test script to verify functionality:
```bash
python test_marking_scheme.py
```

This will test:
- Marking scheme upload
- Document upload with marking scheme
- Bulk upload with marking scheme
- Job creation with marking scheme

## Migration

If upgrading from a previous version, run the migration script:
```bash
python migrate_db.py
```

This will:
- Create the `marking_schemes` table
- Add the `marking_scheme_id` column to the `grading_jobs` table

## Future Enhancements

Potential improvements for future versions:
- Marking scheme templates and library
- Marking scheme versioning
- Advanced marking scheme formats (JSON, XML)
- Marking scheme sharing between users
- Marking scheme analytics and usage statistics
