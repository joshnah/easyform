#!/usr/bin/env python3
import argparse
import logging
from .llm_client import get_openai_client, test_openai
from . import llm_client
from .context_extractor import extract_context
import os
import json
from .advanced_form_filler import fill_in_form
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(
        prog='filler_agent',
        description='Extract personal information and fill forms using GPT-4.'
    )
    parser.add_argument('--contextDir', type=str, required=False, help='Path to directory that contains/should contain context_data.json')
    parser.add_argument('--form', type=str, help='Path to form to fill.')
    parser.add_argument('--output', type=str, default=None, help='Output path for the filled form.')
    parser.add_argument('--context', type=str, default=None, help='Path to context JSON file for filling form.')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging.')
    parser.add_argument('--test-api', action='store_true', help='Test OpenAI API connectivity.')
    parser.add_argument('--provider', choices=['openai', 'groq', 'anythingllm', 'local'], default=None, help='Specify LLM provider to use (openai or groq).')
    parser.add_argument('--printFilled', action='store_true', help='After filling a form, print the plain text of the filled document to stdout for inspection.')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    # Set LLM provider if specified
    if args.provider:
        llm_client.DEFAULT_PROVIDER = args.provider
        logging.info(f"LLM provider set to: {args.provider}")
    # Handle OpenAI API test
    if args.test_api:
        get_openai_client()
        test_openai()
        return
    # Helper to update date fields in context dict
    def update_context_with_date_fields(context_data):
        today = datetime.today()
        context_data['current_day'] = today.strftime('%d')
        context_data['current_month'] = today.strftime('%m')
        context_data['current_year'] = today.strftime('%Y')
        context_data['current_date (MM/DD/YYYY)'] = today.strftime('%m/%d/%Y')
        context_data['current_date (DD/MM/YYYY)'] = today.strftime('%d/%m/%Y')
        context_data['current_date (MM-DD-YYYY)'] = today.strftime('%m-%d-%Y')
        context_data['current_date (DD-MM-YYYY)'] = today.strftime('%d-%m-%Y')
        context_data['current_date (YYYY/MM/DD)'] = today.strftime('%Y/%m/%d')
        context_data['current_date (YYYY-MM-DD)'] = today.strftime('%Y-%m-%d')
        return context_data
    # Decide on the effective context directory (if provided via the new flag,
    # fall back to the deprecated one to preserve behaviour)
    effective_context_dir = args.contextDir

    # Handle context extraction (when the user explicitly passes a contextDir
    # without a --form).  We treat the presence of --contextDir without --form
    # as a request to (re)generate context_data.json.
    if effective_context_dir and not args.form:
        output_path = args.output or os.path.join(effective_context_dir, 'context_data.json')
        if os.path.exists(output_path):
            logging.info(f'Context data already exists at {output_path}, skipping extraction.')
            # Even if skipping extraction, update date fields
            with open(output_path, 'r', encoding='utf-8') as f:
                context_data = json.load(f)
            context_data = update_context_with_date_fields(context_data)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(context_data, f, ensure_ascii=False, indent=4)
        else:
            logging.info(f'Extracting context from: {effective_context_dir}')
            personal_info = extract_context(effective_context_dir, args.provider)
            personal_info = update_context_with_date_fields(personal_info)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(personal_info, f, ensure_ascii=False, indent=4)
            logging.info(f'Context data written to {output_path}')

        # Build and persist aggregated corpus so that later filling can reuse
        # it without re-OCRing everything.
        try:
            from .context_extractor import scan_context_dir, aggregate_text
            files = scan_context_dir(effective_context_dir)
            corpus = aggregate_text(files)
            corpus_path = os.path.join(effective_context_dir, 'aggregated_corpus.txt')
            with open(corpus_path, 'w', encoding='utf-8') as cf:
                cf.write(corpus)
            logging.info(f'Aggregated corpus written to {corpus_path}')
        except Exception as e:
            logging.error(f'Failed to build aggregated corpus: {e}')
        return
    if args.form:
        if not effective_context_dir:
            logging.error('You must specify --contextDir when using --form so the program knows where to find context_data.json and related resources.')
            return
        logging.info(f'Filling form: {args.form}')
        context_path = args.context or os.path.join(effective_context_dir, 'context_data.json')
        if not os.path.exists(context_path):
            logging.warning(f"Context JSON file not found at {context_path}. Creating new context data from available documents in the folder.")
            # Extract context fresh and persist
            try:
                context_data = extract_context(effective_context_dir, args.provider)
                context_data = update_context_with_date_fields(context_data)
                with open(context_path, 'w', encoding='utf-8') as f:
                    json.dump(context_data, f, ensure_ascii=False, indent=4)
                logging.info(f"Created new context data at {context_path}.")

                # Also (re)build aggregated corpus if missing
                try:
                    from .context_extractor import scan_context_dir, aggregate_text
                    files = scan_context_dir(effective_context_dir)
                    corpus = aggregate_text(files)
                    corpus_path = os.path.join(effective_context_dir, 'aggregated_corpus.txt')
                    with open(corpus_path, 'w', encoding='utf-8') as cf:
                        cf.write(corpus)
                    logging.info(f"Aggregated corpus written to {corpus_path}")
                except Exception as e:
                    logging.error(f"Failed to build aggregated corpus: {e}")
            except Exception as e:
                logging.error(f"Failed to create context data: {e}")
                return
        else:
            with open(context_path, 'r', encoding='utf-8') as f:
                context_data = json.load(f)
        context_dir = effective_context_dir
        context_data = update_context_with_date_fields(context_data)
        # Save updated context before using it
        with open(context_path, 'w', encoding='utf-8') as f:
            json.dump(context_data, f, ensure_ascii=False, indent=4)
        output_path = args.output or args.form.replace('.docx', '_filled.docx')
        keys = list(context_data.keys())
        fill_in_form(keys, args.form, context_dir, args.provider, output_path)
        logging.info(f"Filled form saved to {output_path}")

        # Optionally print the filled document's text content for quick inspection
        if args.printFilled:
            try:
                from .context_extractor import extract_docx, extract_pdf
                ext = os.path.splitext(output_path)[1].lower()
                if ext == '.docx':
                    text = extract_docx(output_path)
                elif ext == '.pdf':
                    text = extract_pdf(output_path)
                else:
                    logging.warning(f"Cannot extract text from unsupported file type: {ext}")
                    text = ''

                print("\n===== Filled Document Text =====\n")
                print(text)
                print("\n===== End of Filled Document Text =====\n")
            except Exception as e:
                logging.error(f"Failed to extract and print filled document text: {e}")
        return


if __name__ == '__main__':
    main() 