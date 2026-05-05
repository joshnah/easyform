/**
 * Hand-written TypeScript types for the back2 HTTP API.
 *
 * Mirrors the Pydantic schemas in:
 * - back2/api/native.py  — native (document-first) endpoints
 * - back2/api/compat.py  — legacy compat endpoints used by the frontend
 *
 * To regenerate from a running server (preferred — keeps these in sync):
 *   1. Start backend: `mise run sb`
 *   2. Run: `npm run gen:api-types`
 *   3. Switch imports from "@/types/backend" to "@/types/backend.gen".
 */

export type Provider = "openai" | "groq" | "anythingllm" | "local";

// ---------------------------------------------------------------------------
// Compat surface — what the existing frontend calls.
// ---------------------------------------------------------------------------

export interface FillEntry {
  lines: string;
  number_of_fill_spots: number;
  context_keys: (string | null)[];
  filled_lines: string;
}

export interface CheckboxEntry {
  lines: string;
  checkbox_positions: [number, number][];
  checkbox_values: string[];
  context_key: string | null;
  checked_indices: number[];
}

// /form/text
export interface ExtractFormTextRequest {
  form_path: string;
}
export interface ExtractFormTextResponse {
  text: string;
}

// /pattern/detect
export interface DetectPatternRequest {
  text: string;
  provider: Provider;
}
export interface DetectPatternResponse {
  pattern: string;
}

// /fill-entries/detect
export interface DetectFillEntriesRequest {
  lines: string[];
  keys: string[];
  pattern: string;
  provider: Provider;
}
export interface DetectFillEntriesResponse {
  entries: FillEntry[];
}

// /fill-entries/process
export interface ProcessFillEntriesRequest {
  entries: FillEntry[];
  context_dir: string;
  pattern: string;
  provider: Provider;
}
export interface ProcessFillEntriesResponse {
  entries: FillEntry[];
}

// /context/{read,add,update,delete,extract}
export interface ContextDirRequest {
  context_dir: string;
}
export interface ContextKeyValueRequest {
  context_dir: string;
  key: string;
  value: string;
}
export interface ContextKeyRequest {
  context_dir: string;
  key: string;
}
export interface ExtractContextRequest {
  context_dir: string;
  provider: Provider;
}
export interface ContextResponse {
  context: Record<string, string | null>;
}

// /checkbox-entries/{detect,process}
export interface DetectCheckboxEntriesRequest {
  lines: string[];
  keys: string[];
}
export interface DetectCheckboxEntriesResponse {
  entries: CheckboxEntry[];
}
export interface ProcessCheckboxEntriesRequest {
  entries: CheckboxEntry[];
  context_dir: string;
  keys: string[];
  provider: Provider;
}
export interface ProcessCheckboxEntriesResponse {
  entries: CheckboxEntry[];
}

// /pdf/fill, /docx/fill
export interface FillFormRequest {
  fill_entries: FillEntry[];
  checkbox_entries: CheckboxEntry[];
  form_path: string;
  output_path: string | null;
}
export interface FillFormResponse {
  output_path: string;
}

// ---------------------------------------------------------------------------
// Native surface — recommended for new clients.
// ---------------------------------------------------------------------------

export interface FieldRequirement {
  field_id: string;
  field_text: string;
  line_number: number;
  placeholder_pattern: string;
  surrounding_context: string;
  field_type: string | null;
  context_key: string | null;
  match_position: number | null;
  value: string | null;
}

export interface AnalyzeDocumentRequest {
  document_path: string;
  provider: Provider;
}
export interface AnalyzeDocumentResponse {
  field_requirements: FieldRequirement[];
  metadata: {
    document_text: string;
    total_fields: number;
    placeholder_pattern: string;
    document_path: string;
  };
}

export interface SearchContextRequest {
  field_requirements: FieldRequirement[];
  context_dir: string;
  provider: Provider;
}
export interface SearchContextResponse {
  field_requirements: FieldRequirement[];
}

export interface FillDocumentRequest {
  document_path: string;
  document_text: string;
  field_requirements: FieldRequirement[];
  save: boolean;
  output_path?: string | null;
  extension?: string | null;
}
export interface FillDocumentResponse {
  saved: boolean;
  output_path: string | null;
  fill_result: FillResult | null;
}
export interface FillResult {
  original_text: string;
  filled_text: string;
  filled_fields: string[];
  unfilled_fields: string[];
  success: boolean;
}

export interface ProcessDocumentRequest {
  document_path: string;
  context_dir: string;
  output_path?: string | null;
  provider: Provider;
}

export interface HealthResponse {
  status: "ok";
  workflow: "document-first";
}
