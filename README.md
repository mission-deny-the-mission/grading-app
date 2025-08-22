# Document Grading Web App

A modern Python web application that uses AI to grade documents. Supports multiple LLM providers including OpenRouter, Claude API, and LM Studio for local inference.

## Features

- **Multi-Format Support**: Upload Word documents (.docx) and PDF files
- **Multiple AI Providers**: 
  - OpenRouter (access to Claude, GPT, and other models)
  - Claude API (direct Anthropic integration)
  - LM Studio (local model inference)
- **Marking Scheme Support**: Upload grading rubrics and marking schemes to guide AI grading
- **Bulk Processing**: Upload and process multiple documents in the background
- **Job Management**: Track and monitor grading jobs with real-time progress
- **Background Processing**: Celery-based task queue for scalable processing
- **Database Storage**: SQLite/PostgreSQL support for job and result persistence
- **Configurable Prompts**: Customize grading criteria and instructions
- **Modern UI**: Beautiful, responsive interface with Bootstrap 5
- **Real-time Processing**: AJAX-based upload and grading
- **Result Export**: Download grading results as text files
- **Sample Prompts**: Pre-built templates for different document types

## Screenshots

The application features a modern, gradient-based design with:
- Clean upload interface
- Configurable AI provider selection
- Customizable grading prompts
- Real-time status indicators
- Professional result display

## Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package installer)

### Setup

1. **Clone or download the project**
   ```bash
   git clone <your-repo>
   cd grading-app
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   # Linux/macOS (bash)
   source venv/bin/activate
   # fish shell
   source venv/bin/activate.fish
   # Windows (PowerShell)
   venv\\Scripts\\Activate.ps1
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Redis** (required for background processing)
   ```bash
   # Ubuntu/Debian
   sudo apt-get install redis-server
   sudo systemctl start redis
   
   # macOS
   brew install redis
   brew services start redis
   
   # Or run manually
   redis-server
   ```

5. **Set up environment variables** (optional)
   Create a `.env` file in the project root:
   ```env
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   CLAUDE_API_KEY=your_claude_api_key_here
   LM_STUDIO_URL=http://localhost:1234/v1
   SECRET_KEY=your_secret_key_here
   DATABASE_URL=sqlite:///grading_app.db
   ```

6. **Run the application**
   
   **Option A: Full services (recommended)**
   ```bash
   ./start_services.sh
   ```
   
   **Option B: Basic mode (single upload only)**
   ```bash
   python app.py
   ```

7. **Access the web interface**
   Open your browser and go to: `http://localhost:5000`

## Configuration

### API Keys Setup

#### OpenRouter
1. Visit [OpenRouter](https://openrouter.ai)
2. Sign up and add payment method
3. Generate an API key (starts with "sk-or-")
4. Add to configuration in the web interface

#### Claude API
1. Visit [Anthropic Console](https://console.anthropic.com)
2. Create account and add payment method
3. Generate an API key (starts with "sk-ant-")
4. Add to configuration in the web interface

#### LM Studio (Local)
1. Download [LM Studio](https://lmstudio.ai)
2. Install and launch the application
3. Download a model (e.g., Llama 2, Mistral)
4. Start the local server
5. Test connection in the web interface

## Usage

### Basic Grading (Single Upload)

1. **Upload Document**: Select a .docx or .pdf file (max 100MB)
2. **Upload Marking Scheme** (Optional): Select a .docx, .pdf, or .txt file with grading criteria
3. **Choose AI Provider**: Select from OpenRouter, Claude, or LM Studio
4. **Customize Prompt**: Modify grading instructions or use sample prompts
5. **Grade**: Click "Grade Document" and wait for results
6. **Review**: View detailed feedback and download results

### Bulk Processing

1. **Create Job**: Go to "Bulk Upload" and configure grading parameters
   - Set job name, description, and priority
   - Choose AI provider and model
   - Configure grading prompt
   - **Optional**: Upload a marking scheme for consistent grading
   - Click "Create Job" to generate a job ID
2. **Upload Files**: Select multiple documents (up to 50 files)
   - Files will be associated with the created job
   - Processing starts automatically after upload
3. **Monitor Progress**: Track job progress on the Jobs page
   - Real-time progress indicators
   - Status updates for each submission
4. **Review Results**: View individual submissions and download results

### Job Management

- **View All Jobs**: Monitor all grading jobs and their status
- **Job Details**: Comprehensive view of individual jobs with:
  - Job overview and progress tracking
  - Submission list with status indicators
  - Individual submission details and grading results
  - Export functionality for job results
- **Real-time Updates**: Progress bars and status indicators
- **Error Handling**: Detailed error messages for failed submissions
- **API Access**: RESTful API endpoints for programmatic access

### Sample Prompts

The application includes pre-built prompts for:
- **Academic Essays**: Thesis, arguments, research quality, structure
- **Business Reports**: Executive summary, data analysis, recommendations
- **Creative Writing**: Narrative structure, character development, style
- **Technical Documents**: Accuracy, clarity, organization, completeness

### Custom Prompts

You can create custom grading criteria by:
1. Writing specific instructions in the prompt field
2. Including evaluation criteria
3. Specifying desired output format
4. Adding context about the document type

### Marking Schemes

The application supports uploading marking schemes and grading rubrics:

- **Supported Formats**: DOCX, PDF, TXT files
- **Automatic Integration**: Marking scheme content is automatically included in AI prompts
- **Consistent Grading**: Ensures all documents are graded using the same criteria
- **View and Download**: Access marking scheme content from job details
- **Bulk Processing**: Apply the same marking scheme to multiple documents

**Example Marking Scheme Format:**
```
GRADING RUBRIC FOR ESSAYS

CRITERIA:
1. Thesis Statement (20 points)
   - Clear and specific thesis
   - Well-argued position

2. Content and Analysis (30 points)
   - Relevant evidence and examples
   - Logical argument development

GRADING SCALE:
A (90-100): Excellent work
B (80-89): Good work
C (70-79): Satisfactory work
```

## File Structure

```
grading-app/
├── app.py                 # Flask app initialization, blueprint registration, shims
├── routes/                # Route blueprints (moved from app.py)
│   ├── main.py            # UI pages: index, config, jobs, bulk upload
│   ├── upload.py          # Upload endpoints (single, marking scheme, bulk)
│   ├── api.py             # REST API endpoints (jobs, submissions, saved configs, batches)
│   └── batches.py         # Batch UI pages and creation endpoint
├── utils/                 # Helper modules
│   ├── text_extraction.py # DOCX/PDF/TXT extraction helpers
│   └── llm_providers.py   # OpenRouter/Claude/LM Studio integrations
├── models.py              # Database models
├── tasks.py               # Celery background tasks
├── celeryconfig.py        # Celery configuration
├── requirements.txt       # Python dependencies
├── start_services.sh      # Full service startup script
├── run.sh                 # Basic startup script
├── templates/             # HTML templates
└── uploads/               # Temporary file storage
```

Notes:
- API routes now live under `routes/api.py` via a Flask blueprint. Legacy `url_for` usages like `url_for('create_batch')` remain supported via app-level aliases.
- Provider calls and text extraction logic are centralized in `utils/`.

## API Integration Details

### OpenRouter
- Supports multiple models (Claude, GPT, etc.)
- Pay-per-use pricing
- High availability and reliability

### Claude API
- Direct Anthropic integration
- Latest Claude models
- Consistent performance

### LM Studio
- Local model inference
- No internet required
- Custom model support
- Free to use

## Security Features

- File size limits (100MB max)
- Secure filename handling
- Temporary file cleanup
- API key protection
- Input validation

## Troubleshooting

### Common Issues

1. **"Provider not available" error**
   - Check API keys in configuration
   - Verify API provider status
   - Test connection in config page

2. **File upload errors**
   - Ensure file is .docx or .pdf
   - Check file size (max 16MB)
   - Verify file is not corrupted

3. **LM Studio connection fails**
   - Ensure LM Studio is running
   - Check server URL (default: http://localhost:1234/v1)
   - Verify model is loaded in LM Studio

4. **API rate limits**
   - OpenRouter and Claude have usage limits
   - Check your account status
   - Consider upgrading plan if needed

### Performance Tips

- Use LM Studio for high-volume grading
- Optimize prompts for faster processing
- Keep documents under 10MB for best performance
- Use appropriate model size for your needs

## Development

### Adding New Providers

To add a new LLM provider:

1. Implement provider functions in `utils/llm_providers.py`
2. Use them from upload routes in `routes/upload.py`
3. Update provider selection in templates and `DEFAULT_MODELS` if applicable
4. Add configuration options (env vars) and tests

### Customizing Styles

The application uses Bootstrap 5 with custom CSS. Modify:
- `templates/base.html` for global styles
- Individual template files for specific styling

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review API provider documentation
3. Test with sample documents
4. Verify configuration settings

---

**Note**: This application requires API keys for cloud providers (OpenRouter, Claude). LM Studio is free but requires local installation and model downloads.
