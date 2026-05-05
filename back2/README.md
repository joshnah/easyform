# back2

> **Canonical docs are in [docs/back2/](../docs/back2/)** — start with [docs/back2/README.md](../docs/back2/README.md) for the doc map, [architecture.md](../docs/back2/architecture.md) for the deep-dive, and [api-reference.md](../docs/back2/api-reference.md) for every endpoint. This file is kept next to the code as a quick orientation.

A FastAPI backend that fills PDF / DOCX / TXT forms by (1) analyzing the document for placeholders, (2) searching a context directory for the values, and (3) writing the filled document back. Runs on port 8000.

## Layout

```
back2/
├── server.py              # uvicorn launcher (port 8000)
├── cli.py                 # CLI: pipeline mode or `--server`
├── schemas.py             # FieldRequirement dataclass
├── config.json            # AnythingLLM config (sample placeholders)
├── tokenizer.json         # HuggingFace tokenizer (optional, for token budgeting)
│
├── api/                   # FastAPI app
│   ├── __init__.py            # builds app, applies CORS, mounts routers
│   ├── native.py              # native (document-first) endpoints
│   ├── compat.py              # legacy compat endpoints (delegate to back/)
│   └── context_store.py       # context_data.json read/write helpers
│
├── pipeline/              # phase orchestration
│   ├── analyzer.py            # phase 1: detect fields, infer types/keys
│   ├── searcher.py            # phase 2: search context for values
│   ├── workflow.py            # 3-phase orchestrator + main_workflow
│   └── prompts.py             # LLM prompts
│
├── extraction/            # read documents, detect placeholder patterns
│   ├── text.py                # PDF / DOCX / TXT / MD / JSON → text
│   └── patterns.py            # pick best placeholder regex
│
├── fillers/               # write filled documents
│   ├── base.py                # BaseFiller, FillResult, ensure_ext
│   ├── txt.py                 # TxtFiller
│   ├── docx.py                # DocxFiller
│   └── pdf.py                 # PdfFiller
│
├── providers/             # LLM provider abstraction
│   ├── base.py                # LLMProvider ABC
│   ├── openai.py              # OpenAIProvider
│   ├── groq.py                # GroqProvider
│   ├── anythingllm.py         # AnythingLLMProvider
│   └── local.py               # LocalProvider (Genie .exe, Windows)
│
└── utils/                 # pure utilities
    ├── paths.py               # resource resolver (PyInstaller-aware)
    ├── tokenization.py        # count_tokens with char-fallback
    ├── text_splitter.py       # recursive char splitter (langchain-free)
    └── json_parser.py         # robust LLM-response JSON parser
```

## Quickstart

```bash
# Install (base deps; add `requirements-extras.txt` for the heavy /context/extract path)
pip install -r requirements.txt

# Run on port 8000
mise run sb                              # uvicorn back2.api:app --reload --port 8000
# or
python -m back2.server                   # no reload
# or
python -m back2.cli --server --port 8000 # back2's own CLI

# Smoke check
curl :8000/health                        # {"status":"ok","workflow":"document-first"}
open http://localhost:8000/docs          # Swagger UI

# Run the full pipeline from the CLI
python -m back2.cli --document form.pdf --context-dir ./context --provider groq
```

## Programmatic use

```python
from back2.pipeline import main_workflow

result = main_workflow(
    document_path="form.pdf",
    context_dir="./context",
    output_path="filled.pdf",
    provider="groq",
)
```

## Endpoint surface (summary)

Native (document-first):

- `GET /health`, `GET /providers`, `GET /document/info`, `GET /context/list`
- `POST /document/analyze`, `POST /context/search`, `POST /document/fill`, `POST /process`

Compat (legacy frontend):

- `POST /form/text`, `POST /pattern/detect`
- `POST /fill-entries/{detect,process}`, `POST /checkbox-entries/{detect,process}`
- `POST /context/{read,add,update,delete,extract}`
- `POST /docx/fill`, `POST /pdf/fill`

Compat handlers lazily delegate to the legacy `back/` package so PDF overlay and OCR-based context extraction keep working unchanged. See [docs/back2/migration.md](../docs/back2/migration.md) for the cutover plan.
