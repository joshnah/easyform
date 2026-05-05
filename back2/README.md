# Back2 - Document-First Form Filling Workflow

This directory contains a modified backend workflow that follows a **document-first approach** instead of the context-first approach used in the original `back` folder.

## Workflow Comparison

### Original Workflow (back/)
1. Extract context from context directory first
2. Try to fill the document with available context
3. Limited understanding of what the document actually needs

### New Workflow (back2/)
1. **Analyze document** to understand what fields need to be filled
2. **Search context directory** for the specific information required
3. **Fill document** with found information
4. Save all discovered information to `context_data.json` for future use

## Key Features

- **Document Analysis**: Identifies all fillable fields and their types
- **Context Search**: Searches for specific information based on document requirements
- **Smart Mapping**: Maps document fields to context keys using LLM analysis
- **Persistent Context**: Saves discovered information for future use
- **Comprehensive Logging**: Detailed temporary files for debugging
- **API Integration**: FastAPI server for programmatic access

## File Structure

```
back2/
├── __init__.py              # Package initialization
├── document_analyzer.py     # Document analysis and field detection
├── context_searcher.py      # Context directory search
├── form_filler.py          # Document filling logic
├── workflow.py             # Main workflow orchestrator
├── api.py                  # FastAPI server
├── cli.py                  # Command-line interface
├── test_api_process.py     # API testing script
├── llm_client.py           # LLM client (copied from back)
├── text_extraction.py     # Text extraction utilities
├── pattern_detection.py   # Placeholder pattern detection
└── prompts.py             # LLM prompts
```

## Usage

### Command Line Interface

```bash
# Basic usage
python -m back2.cli --document form.pdf --context-dir ./context

# With specific output and provider
python -m back2.cli --document form.pdf --context-dir ./context --output filled.pdf --provider openai

# Run API server
python -m back2.cli --server --port 8001
```

### API Server

```bash
# Start server
python -m back2.api

# Or via CLI
python -m back2.cli --server
```

### Programmatic Usage

```python
from back2.workflow import main_workflow

result = main_workflow(
    document_path="form.pdf",
    context_dir="./context",
    output_path="filled.pdf",
    provider="groq"
)
```

## API Endpoints

- `GET /health` - Health check
- `POST /document/analyze` - Analyze document structure
- `POST /context/search` - Search context directory
- `POST /process` - Complete workflow
- `GET /document/info` - Get document information
- `GET /context/list` - List context files

## Testing

```bash
# Test the API workflow
python back2/test_api_process.py --form form.pdf --contextDir ./context --provider groq
```

## Dependencies

Same as the original `back` folder:
- PyMuPDF (for PDF processing)
- python-docx (for DOCX processing)
- FastAPI (for API server)
- Requests (for API calls)
- OpenAI/Groq/AnythingLLM clients

## Advantages of Document-First Approach

1. **Better Understanding**: Analyzes what the document actually needs
2. **Targeted Search**: Only searches for information that's actually required
3. **Higher Accuracy**: Matches fields based on context and meaning
4. **Efficiency**: Avoids processing unnecessary context information
5. **Flexibility**: Can handle documents with varied field types and layouts
6. **Debugging**: Comprehensive temporary files for troubleshooting
