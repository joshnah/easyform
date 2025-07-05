# easyform

## Backend API (FastAPI)

Run the server (with auto-reload) and open the interactive docs:

```bash
# Preferred
python -m back.server

# Equivalent (explicit Uvicorn invocation)
uvicorn back.api:app --host 0.0.0.0 --port 8000 --reload
```

Once running, visit:

* Swagger UI: http://localhost:8000/docs  
* ReDoc:      http://localhost:8000/redoc  
* Raw OpenAPI JSON: http://localhost:8000/openapi.json

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/form/text` | Convert a form file (PDF/DOCX) to plain text. |
| POST | `/pattern/detect` | Detect placeholder pattern from form text. |
| POST | `/fill-entries/detect` | Detect fill entries in form lines. |
| POST | `/fill-entries/process` | Process & fill entries using context data. |
| POST | `/checkbox-entries/detect` | Detect checkbox groups (with their checkbox positions, labels, etc.) in form lines. |
| POST | `/checkbox-entries/process` | Determine which boxes to check using context & update entries. |
| POST | `/context/read` | Read `context_data.json` in a context directory. |
| POST | `/context/add` | Add/update a key-value pair in `context_data.json`. |
| POST | `/context/extract` | Run full context extraction pipeline for a dir (writes/returns `context_data.json`). |
| POST | `/docx/fill` | Fill a DOCX form using pre-computed `FillEntry` & `CheckboxEntry` payloads (no detection on server). |
| POST | `/pdf/fill` | Fill a PDF form (interactive or flat overlay) using pre-computed entries. |
| GET  | `/health` | Simple health check. |

### JSON Schemas

#### FillEntry

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FillEntry",
  "type": "object",
  "properties": {
    "lines": {
      "type": "string",
      "description": "Original multiline string that contains the placeholders."
    },
    "number_of_fill_spots": {
      "type": "integer",
      "description": "Total number of placeholder occurrences inside `lines`."
    },
    "context_keys": {
      "type": "array",
      "items": {
        "type": ["string", "null"]
      },
      "description": "List of context key names (or null) per placeholder position."
    },
    "filled_lines": {
      "type": "string",
      "description": "Same as `lines` but with placeholders replaced by actual values (if available)."
    }
  },
  "required": ["lines", "number_of_fill_spots", "context_keys"]
}
```

#### CheckboxEntry

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CheckboxEntry",
  "type": "object",
  "properties": {
    "lines": {
      "type": "string",
      "description": "Multiline text snippet containing the checkbox group."
    },
    "checkbox_positions": {
      "type": "array",
      "items": {
        "type": "array",
        "items": { "type": "integer" },
        "minItems": 2,
        "maxItems": 2
      },
      "description": "List of (lineIndex, charIndex) tuples where each checkbox is located within `lines`."
    },
    "checkbox_values": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Human-readable label text next to each checkbox."
    },
    "context_key": {
      "type": ["string", "null"],
      "description": "Context key that this checkbox group maps to (if inferable)."
    },
    "checked_indices": {
      "type": "array",
      "items": { "type": "integer" },
      "description": "Indices into `checkbox_values` that should be checked." 
    }
  },
  "required": ["lines", "checkbox_positions", "checkbox_values"]
}
```

The FastAPI documentation UI (`/docs`) automatically exposes these schemas for all request/response payloads.

## Quick Local Test Run
```bash
# 1) Create & activate a virtual environment (first time only)
python3 -m venv .venv
source .venv/bin/activate

# 2) Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3) Run the demo
chmod +x test_run.sh  # if not already executable
./test_run.sh         # optional CLI flags can be appended
```

The script executes:

```bash
python -m back.cli --contextDir ./test_context --form ./form_pdf_long.pdf
```

After completion a filled PDF will be written next to the original file.

---

If you just want to start the FastAPI server instead:

```bash
uvicorn back.api:app --reload
```

and navigate to `http://127.0.0.1:8000/docs` for the interactive swagger UI.
