# EasyForm
An LLM-powered form filler using on-device user documents - can run entirely offline, ensuring accuracy, privacy with great user experience

> Detailed backend documentation lives in [docs/back2/](docs/back2/).

## Dependencies
1. Backend:
```bash
python3 -m venv .venv
source .venv/bin/activate ## or .venv\Scripts\Activate.ps1 on window
pip install --upgrade pip
pip install -r requirements.txt
```
2. Frontend:
```bash
cd front
npm install
``` 

TODO: Download edge AI model

## Getting started on local
1. Run backend

```bash
# Preferred
python -m back.server

# Equivalent (explicit Uvicorn invocation)
uvicorn back.api:app --host 0.0.0.0 --port 8000 --reload
```

Once running, you can visit the API documentation at:

* Swagger UI: http://localhost:8000/docs  
* ReDoc:      http://localhost:8000/redoc  
* Raw OpenAPI JSON: http://localhost:8000/openapi.json

2. Run frontend app in another terminal

```bash
cd front
npm run start:dev
```
The app will appear on the screen for you. Choose a provider and provide API key on the screen. Try to start with an online provider to understand the workflow first.


3. Demo documents
We have also prepare some mock documents:
- `./back/test_form.pdf`: a mock pdf form file
- `./back/test_context`: a mock context directory

After processing, a `context_data.json` file will be generated in your context folder. This file helps speed up future runs. If you want to start from scratch, you can safely delete it.

## Quick API Test Run
```bash
# 1) Ensure the FastAPI server is running
python -m back.server

# 2) In another terminal (or after the server is up) execute:
python test_api_process.py   --form ./back/test-form.pdf  --contextDir ./back/test_context/ --provider anythingllm
# Optional flags:
#   --base http://localhost:8000   # non-default host
#   --out  ./filled_output.pdf     # custom output path
```

The script walks through the entire API pipeline:
1. Health-check
2. Context extraction
3. Text extraction & pattern detection
4. Fill-entry & checkbox detection + processing
5. Calls the appropriate `/docx/fill` or `/pdf/fill` endpoint and prints the resulting output path.

## Packaging on window x64
See [package_with_model.bat](package_with_model.bat) for more info

## Local installation of package
After completing the packaging process, an `EasyForm.msix` file will be generated. To install it locally, you must sign the package. Refer to the [self_signing.ps1](self_signing.ps1) script for detailed instructions on self-signing the package.
