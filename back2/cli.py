"""
Command-line interface for back2 document-first workflow.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from back2.workflow import main_workflow


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="EasyForm Back2 - Document-first form filling workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python -m back2.cli --document form.pdf --context-dir ./context

  # With specific output path and provider
  python -m back2.cli --document form.pdf --context-dir ./context --output filled_form.pdf --provider openai

  # Run API server
  python -m back2.cli --server --port 8001
        """,
    )

    # Main workflow arguments
    parser.add_argument(
        "--document", "-d", help="Path to document to fill (PDF or DOCX)"
    )
    parser.add_argument(
        "--context-dir", "-c", help="Directory containing context information"
    )
    parser.add_argument(
        "--output", "-o", help="Output path for filled document (optional)"
    )
    parser.add_argument(
        "--provider",
        "-p",
        choices=["openai", "groq", "anythingllm"],
        default="groq",
        help="LLM provider to use (default: groq)",
    )

    # Server mode
    parser.add_argument(
        "--server",
        "-s",
        action="store_true",
        help="Run API server instead of CLI workflow",
    )
    parser.add_argument(
        "--port", type=int, default=8001, help="Port for API server (default: 8001)"
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host for API server (default: 0.0.0.0)"
    )

    # Other options
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--save-temp", action="store_true", help="Keep temporary files after completion"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.server:
        run_server(args)
    else:
        if not args.document or not args.context_dir:
            parser.error("--document and --context-dir are required for workflow mode")

        if not os.path.exists(args.document):
            print(f"Error: Document not found: {args.document}")
            sys.exit(1)

        if not os.path.exists(args.context_dir):
            print(f"Error: Context directory not found: {args.context_dir}")
            sys.exit(1)

        run_workflow(args)


def run_workflow(args):
    """Run the main workflow."""
    try:
        print(f"Starting document-first workflow...")
        print(f"Document: {args.document}")
        print(f"Context Directory: {args.context_dir}")
        print(f"Provider: {args.provider}")

        if args.output:
            print(f"Output: {args.output}")

        # Run the workflow
        result = main_workflow(
            document_path=args.document,
            context_dir=args.context_dir,
            output_path=args.output,
            provider=args.provider,
        )

        # Print summary
        print(f"\n{'='*50}")
        print(f"WORKFLOW COMPLETED")
        print(f"{'='*50}")
        print(f"Success: {result['filling']['success']}")
        print(f"Fields found: {result['analysis']['total_fields_found']}")
        print(f"Fields filled: {result['filling']['fields_filled']}")
        print(f"Fields unfilled: {result['filling']['fields_unfilled']}")
        print(f"Output document: {result['output_document']}")

        if result["context_search"]["missing_keys"]:
            print(f"Missing context keys: {result['context_search']['missing_keys']}")

        if args.verbose:
            print(f"\nDetailed Results:")
            print(json.dumps(result, indent=2))

        if not args.save_temp:
            print(f"\nTemporary files saved in:")
            for name, path in result["temp_directories"].items():
                print(f"  {name}: {path}")

        if result["filling"]["success"]:
            print(f"\n✅ Document successfully filled!")
            sys.exit(0)
        else:
            print(f"\n⚠️  Document partially filled or failed.")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def run_server(args):
    """Run the API server."""
    try:
        import uvicorn
        from back2.api import app

        print(f"Starting Back2 API server...")
        print(f"Host: {args.host}")
        print(f"Port: {args.port}")
        print(f"Access the API at: http://{args.host}:{args.port}")
        print(f"API docs at: http://{args.host}:{args.port}/docs")

        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="info" if args.verbose else "warning",
        )

    except ImportError:
        print("Error: uvicorn is required to run the server")
        print("Install with: pip install uvicorn")
        sys.exit(1)
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
