# Marking Schemes as Files - User Guide

## Overview

The Marking Schemes as Files feature allows you to export your grading rubrics as JSON files, share them with colleagues, and import schemes created by others. You can also upload documents (PDF, Word, or text files) to help create new marking schemes using AI assistance.

## Features

### 1. Export Marking Schemes

Export any marking scheme as a portable JSON file that can be shared, backed up, or imported later.

**Use Cases:**
- Share rubrics with colleagues
- Backup important grading schemes
- Transfer schemes between instances
- Archive previous versions

**How to Export:**

```bash
# Using curl
curl -X GET "http://localhost:5000/api/schemes/{scheme_id}/export" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o my_rubric.json

# Using the web interface
# Navigate to: Schemes → Select Scheme → Export button
```

**Export File Format:**
```json
{
  "schema_version": "1.0",
  "exported_at": "2025-11-18T00:00:00Z",
  "exported_by": "professor@university.edu",
  "scheme": {
    "name": "Essay Grading Rubric",
    "description": "Comprehensive rubric for essay assessment",
    "criteria": [
      {
        "name": "Content Quality",
        "weight": 40,
        "descriptors": [
          {
            "level": "excellent",
            "description": "Demonstrates exceptional understanding",
            "points": 10
          }
        ]
      }
    ]
  }
}
```

### 2. Download Exported Files

After exporting a scheme, download the JSON file to your computer.

**How to Download:**

```bash
# Using curl
curl -X GET "http://localhost:5000/api/schemes/download/{filename}" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o downloaded_rubric.json

# The filename is returned from the export endpoint
```

**Response:**
- Content-Type: `application/json`
- Content-Disposition: `attachment; filename="..."`

### 3. Import Marking Schemes

Import marking schemes from JSON files created by the export feature or manually created.

**Use Cases:**
- Import rubrics from colleagues
- Restore from backups
- Use template schemes
- Migrate from other systems

**How to Import:**

```bash
# Using curl
curl -X POST "http://localhost:5000/api/schemes/import" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d @my_rubric.json

# Using the web interface
# Navigate to: Schemes → Import button → Select file
```

**Response:**
```json
{
  "scheme_id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Essay Grading Rubric",
  "message": "Scheme imported successfully"
}
```

### 4. Upload Documents for AI Conversion

Upload a document (PDF, Word, or text file) containing a grading rubric, and let AI convert it into a structured marking scheme.

**Supported Formats:**
- PDF (`.pdf`)
- Microsoft Word (`.docx`)
- Plain Text (`.txt`)

**Maximum File Size:** 10 MB

**How to Upload:**

```bash
# Using curl
curl -X POST "http://localhost:5000/api/schemes/{scheme_id}/upload-document" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "document=@my_rubric.pdf"

# Using the web interface
# Navigate to: Schemes → Select Scheme → Upload Document button
```

**Response:**
```json
{
  "message": "Document uploaded successfully",
  "task_id": "abc123...",
  "status": "processing",
  "estimated_time": "2-5 minutes"
}
```

**Processing:**
1. File is uploaded and validated
2. Text is extracted from the document
3. AI analyzes the content
4. Structured scheme is generated
5. You review and approve the generated scheme

## API Reference

### Export Scheme

```
GET /api/schemes/<scheme_id>/export
```

**Parameters:**
- `scheme_id` (path): UUID of the scheme to export

**Query Parameters:**
- `filename` (optional): Custom filename for the export

**Response:**
- `200 OK`: Export successful, returns JSON export data
- `404 Not Found`: Scheme doesn't exist
- `403 Forbidden`: No permission to export this scheme

### Download Exported Scheme

```
GET /api/schemes/download/<filename>
```

**Parameters:**
- `filename` (path): Name of the exported file

**Response:**
- `200 OK`: File download started
- `404 Not Found`: File doesn't exist

### Import Scheme

```
POST /api/schemes/import
```

**Request Body:**
```json
{
  "schema_version": "1.0",
  "scheme": {
    "name": "Rubric Name",
    "description": "Description",
    "criteria": [...]
  }
}
```

**Response:**
- `201 Created`: Import successful
- `400 Bad Request`: Invalid JSON or schema validation failed
- `409 Conflict`: Scheme with same name already exists

### Upload Document

```
POST /api/schemes/<scheme_id>/upload-document
```

**Parameters:**
- `scheme_id` (path): UUID of the scheme to attach document to

**Form Data:**
- `document`: File upload (multipart/form-data)

**Response:**
- `202 Accepted`: Upload successful, processing started
- `400 Bad Request`: Invalid file type or size
- `404 Not Found`: Scheme doesn't exist

## Schema Validation

Imported files must conform to this schema:

```json
{
  "schema_version": "1.0",  // Required
  "scheme": {
    "name": "string",        // Required, 1-200 chars
    "description": "string", // Optional
    "criteria": [            // Required, non-empty array
      {
        "name": "string",    // Required
        "weight": number,    // Required, > 0
        "descriptors": [     // Required, non-empty array
          {
            "level": "excellent|good|satisfactory|poor|fail",
            "description": "string",
            "points": number  // >= 0
          }
        ]
      }
    ]
  }
}
```

**Validation Errors:**

If validation fails, you'll receive detailed error messages:

```json
{
  "error": "Schema validation failed",
  "details": [
    {
      "field": "scheme.criteria[0].weight",
      "message": "Weight must be greater than 0"
    }
  ]
}
```

## Best Practices

### Exporting Schemes

1. **Use Descriptive Names**: Include context in the scheme name
   - Good: "Spring 2025 Essay Rubric - Literature"
   - Bad: "Rubric 1"

2. **Add Descriptions**: Explain the purpose and context
   ```json
   "description": "For undergraduate literature essays, 1500-2000 words"
   ```

3. **Version Your Exports**: Include dates or version numbers
   - `essay_rubric_v1_2025-11-18.json`

### Importing Schemes

1. **Validate Before Import**: Check the JSON file for errors
   ```bash
   python -m json.tool my_rubric.json
   ```

2. **Review After Import**: Check that all criteria and descriptors imported correctly

3. **Customize After Import**: Adjust weights and descriptions to fit your needs

### Uploading Documents

1. **Clean Formatting**: Ensure documents are well-formatted
   - Use clear headings
   - Consistent bullet points or numbering
   - Explicit point values

2. **Supported Content**:
   - Rubrics with clear criteria
   - Level descriptions (e.g., "Excellent: 9-10 points")
   - Weight distributions

3. **Review AI Output**: Always review and edit AI-generated schemes
   - Check point allocations
   - Verify criterion weights
   - Adjust level descriptions

## Troubleshooting

### Export Fails

**Error: "Scheme not found"**
- Verify the scheme ID is correct
- Ensure you have permission to access the scheme

**Error: "Unauthorized"**
- Check your authentication token
- Verify you're logged in

### Import Fails

**Error: "Schema validation failed"**
- Check the JSON structure matches the schema
- Ensure all required fields are present
- Verify enum values (e.g., level must be: excellent, good, satisfactory, poor, fail)

**Error: "Invalid JSON"**
- Validate your JSON file:
  ```bash
  python -m json.tool my_rubric.json
  ```
- Check for missing commas, brackets, or quotes

### Upload Fails

**Error: "File too large"**
- Maximum file size is 10 MB
- Compress or split large documents

**Error: "Unsupported file type"**
- Only PDF, DOCX, and TXT are supported
- Convert other formats first

**Error: "Could not extract text"**
- For PDFs: Ensure it's not image-only (use OCR first)
- For DOCX: Ensure it's not corrupted
- Try converting to TXT manually

### Processing Takes Too Long

**Document upload stuck at "processing"**
- Check the task queue status
- Large documents (10MB) can take 5-10 minutes
- Complex PDFs with many pages may timeout

**To check task status:**
```bash
curl -X GET "http://localhost:5000/api/tasks/{task_id}/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Examples

### Example 1: Simple Export and Import

```bash
# 1. Export a scheme
curl -X GET "http://localhost:5000/api/schemes/abc-123/export" \
  -H "Authorization: Bearer $TOKEN" \
  -o backup.json

# 2. Import on another instance
curl -X POST "http://localhost:5000/api/schemes/import" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @backup.json
```

### Example 2: Share a Rubric with Colleague

```bash
# 1. Professor A exports their rubric
curl -X GET "http://localhost:5000/api/schemes/xyz-789/export" \
  -H "Authorization: Bearer $TOKEN_A" \
  -o essay_rubric.json

# 2. Professor A sends essay_rubric.json to Professor B

# 3. Professor B imports the rubric
curl -X POST "http://localhost:5000/api/schemes/import" \
  -H "Authorization: Bearer $TOKEN_B" \
  -H "Content-Type: application/json" \
  -d @essay_rubric.json
```

### Example 3: Create Scheme from Document

```bash
# 1. Upload a PDF rubric
curl -X POST "http://localhost:5000/api/schemes/new-scheme/upload-document" \
  -H "Authorization: Bearer $TOKEN" \
  -F "document=@my_rubric.pdf"

# Response includes task_id
# {
#   "task_id": "task_abc123",
#   "status": "processing"
# }

# 2. Check processing status
curl -X GET "http://localhost:5000/api/tasks/task_abc123/status" \
  -H "Authorization: Bearer $TOKEN"

# 3. When complete, review and edit the generated scheme
```

## Security Considerations

1. **File Uploads**: Files are scanned for MIME type mismatches
2. **File Size Limits**: 10 MB maximum to prevent abuse
3. **Authentication**: All endpoints require valid authentication
4. **Authorization**: Users can only export/import their own schemes (or shared schemes)
5. **Path Traversal Prevention**: Filenames are sanitized

## Related Documentation

- [API Documentation](docs/api/openapi.yaml)
- [Marking Schemes Guide](SCHEME_INTEGRATION_GUIDE.md)
- [Deployment Guide](docs/deployment.md)
- [Security Best Practices](docs/security.md)

## Support

For issues or questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review the [API Reference](#api-reference)
- Contact support: support@example.com
- GitHub Issues: https://github.com/user/grading-app/issues

---

*Last Updated*: 2025-11-18
*Feature Version*: 1.0
*Compatibility*: API v1.x
