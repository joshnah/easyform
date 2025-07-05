# easyform

## Backend API (FastAPI)

Run the server:

```bash
uvicorn back.api:app --reload
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/form/text` | Convert a form file (PDF/DOCX) to plain text. |
| POST | `/pattern/detect` | Detect placeholder pattern from form text. |
| POST | `/fill-entries/detect` | Detect fill entries in form lines. |
| POST | `/fill-entries/process` | Process & fill entries using context data. |
| POST | `/context/read` | Read `context_data.json` in a context directory. |
| POST | `/context/add` | Add/update a key-value pair in `context_data.json`. |
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
