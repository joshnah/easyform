import argparse
import json
import os
from pathlib import Path
from typing import List
import requests

BASE_URL_DEFAULT = "http://localhost:8000"
DEFAULT_PROVIDER = "groq"


def post(endpoint: str, payload: dict):
    url = f"{base_url.rstrip('/')}{endpoint}"
    
    # Print request details
    print(f"\n=== API CALL: {endpoint} ===")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    r = requests.post(url, json=payload)
    
    # Print response details
    print(f"Status: {r.status_code}")    
    r.raise_for_status()
    return r.json()


def main():
    parser = argparse.ArgumentParser(
        description="End-to-end API test that mirrors test_run.sh (CLI)"
    )
    parser.add_argument(
        "--form", required=True, help="Path to input form (PDF or DOCX)"
    )
    parser.add_argument(
        "--contextDir",
        required=True,
        help="Directory with context files for extraction",
    )
    parser.add_argument(
        "--base", default=BASE_URL_DEFAULT, help="Base URL of running FastAPI server"
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "groq", "anythingllm", "local"],
        default=DEFAULT_PROVIDER,
        help="LLM provider to use for processing",
    )
    
    parser.add_argument("--out", help="Optional output path for filled file")
    args = parser.parse_args()

    global base_url
    base_url = args.base
    form_path = os.path.abspath(args.form)
    context_dir = os.path.abspath(args.contextDir)
    output_path = os.path.abspath(args.out) if args.out else None

    print("1) Health-check …", end="", flush=True)
    health_url = f"{base_url}/health"
    print(f"\n=== HEALTH CHECK ===")
    print(f"URL: {health_url}")
    health_response = requests.get(health_url)
    print(f"Status: {health_response.status_code}")
    health = health_response.json()
    print(f"Response: {json.dumps(health, indent=2)}")
    print("=" * 50)
    print("OK" if health.get("status") == "ok" else health)

    # 2) Context extraction
    print("2) Extracting context …", flush=True)
    ctx_resp = post(
        "/context/extract", {"context_dir": context_dir, "provider": args.provider}
    )
    context = ctx_resp["context"]
    keys: List[str] = list(context.keys())

    # 3) Extract form text
    print("3) Extracting form text …", flush=True)
    text_resp = post("/form/text", {"form_path": form_path})
    text = text_resp["text"]
    lines = text.split("\n")

    # 4) Detect placeholder pattern
    print("4) Detecting placeholder pattern …", flush=True)
    patt_resp = post("/pattern/detect", {"text": text, "provider": args.provider})
    pattern = patt_resp["pattern"]

    # 5) Detect & process fill entries
    print("5) Fill entries …", flush=True)
    det_fill = post(
        "/fill-entries/detect", {"lines": lines, "keys": keys, "pattern": pattern, "provider": args.provider}
    )
    proc_fill = post(
        "/fill-entries/process",
        {
            "entries": det_fill["entries"],
            "context_dir": context_dir,
            "pattern": pattern,
            "provider": args.provider,
        },
    )

    # 6) Detect & process checkbox entries
    # det_chk = post("/checkbox-entries/detect", {"lines": lines, "keys": keys})
    # proc_chk = post(
    #     "/checkbox-entries/process",
    #     {
    #         "entries": det_chk["entries"],
    #         "context_dir": context_dir,
    #         "keys": keys,
    #         "provider": args.provider,
    #     },
    # )

    # 7) Fill form
    ext = Path(form_path).suffix.lower()
    if ext == ".docx":
        fill_endpoint = "/docx/fill"
        payload = {
            "fill_entries": proc_fill["entries"],
            "checkbox_entries": [],
            "form_path": form_path,
            "output_path": output_path,
        }
    elif ext == ".pdf":
        fill_endpoint = "/pdf/fill"
        payload = {
            "fill_entries": proc_fill["entries"],
            "checkbox_entries": [],
            "form_path": form_path,
            "output_path": output_path,
        }
    else:
        raise SystemExit(f"Unsupported form extension: {ext}")

    print("7) Filling form via", fill_endpoint, "…", flush=True)
    fill_resp = post(fill_endpoint, payload)
    print("Filled file written to:", fill_resp["output_path"])


if __name__ == "__main__":
    main()
