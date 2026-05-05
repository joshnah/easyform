"""End-to-end exercise of the back2 API. Requires a running server."""

import argparse
import json
import os
import time

import requests

BASE_URL_DEFAULT = "http://localhost:8001"
DEFAULT_PROVIDER = "groq"


def post(base_url: str, endpoint: str, payload: dict):
    r = requests.post(f"{base_url.rstrip('/')}{endpoint}", json=payload)
    r.raise_for_status()
    return r.json()


def main():
    parser = argparse.ArgumentParser(description="Exercise the back2 API end-to-end")
    parser.add_argument("--form", required=True, help="Path to input form (PDF or DOCX)")
    parser.add_argument("--contextDir", required=True, help="Directory with context files")
    parser.add_argument("--base", default=BASE_URL_DEFAULT, help="Base URL of running API")
    parser.add_argument(
        "--provider",
        choices=["openai", "groq", "anythingllm", "local"],
        default=DEFAULT_PROVIDER,
    )
    parser.add_argument("--out", help="Output path for the filled file")
    args = parser.parse_args()

    base_url = args.base
    form_path = os.path.abspath(args.form)
    context_dir = os.path.abspath(args.contextDir)
    output_path = os.path.abspath(args.out) if args.out else None
    extension = os.path.splitext(form_path)[1].lstrip(".") or "pdf"

    step_times = {}

    print(f"Document: {form_path}")
    print(f"Context Directory: {context_dir}")
    print(f"API: {base_url}    Provider: {args.provider}")

    # 1) Health
    t0 = time.time()
    health = requests.get(f"{base_url}/health")
    health.raise_for_status()
    step_times["Health"] = time.time() - t0
    print(f"Health: {health.json()}")

    # 2) Analyze
    t0 = time.time()
    analysis = post(
        base_url,
        "/document/analyze",
        {"document_path": form_path, "provider": args.provider},
    )
    step_times["Analyze"] = time.time() - t0

    # 3) Context search
    t0 = time.time()
    context_resp = post(
        base_url,
        "/context/search",
        {
            "field_requirements": analysis["field_requirements"],
            "context_dir": context_dir,
            "provider": args.provider,
        },
    )
    step_times["Context search"] = time.time() - t0

    # 4) Fill
    t0 = time.time()
    fill_payload = {
        "document_path": form_path,
        "document_text": analysis["metadata"]["document_text"],
        "field_requirements": context_resp["field_requirements"],
        "save": True,
        "extension": extension,
    }
    if output_path:
        fill_payload["output_path"] = output_path
    fill_resp = post(base_url, "/document/fill", fill_payload)
    step_times["Fill"] = time.time() - t0

    print("\n=== Step Times ===")
    for step, duration in step_times.items():
        print(f"{step:<16} {duration:.2f}s")
    print(f"Total            {sum(step_times.values()):.2f}s")
    print(f"\nResult: {json.dumps({'saved': fill_resp.get('saved'), 'output_path': fill_resp.get('output_path')}, indent=2)}")


if __name__ == "__main__":
    main()
