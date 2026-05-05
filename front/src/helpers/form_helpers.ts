import { BACKEND_URL } from "@/const";
import type {
  CheckboxEntry,
  ContextResponse,
  DetectFillEntriesResponse,
  ExtractFormTextResponse,
  FillEntry,
  FillFormResponse,
  Provider,
} from "@/types/backend";

const DEFAULT_PROVIDER: Provider = "groq";
export const PROVIDERS: Provider[] = ["groq", "anythingllm", "local", "openai"];

export let provider: Provider = DEFAULT_PROVIDER;

export const setProvider = (newProvider: Provider) => {
  provider = newProvider;
};

async function postJSON<T>(endpoint: string, payload: unknown): Promise<T> {
  const response = await fetch(`${BACKEND_URL}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`${endpoint} ${response.status}: ${detail}`);
  }
  return (await response.json()) as T;
}

export const fetchFormText = async (formPath: string): Promise<string> => {
  const data = await postJSON<ExtractFormTextResponse>("/form/text", {
    form_path: formPath,
  });
  return data.text;
};

export const fetchContext = async (
  contextDir: string,
): Promise<Record<string, string | null>> => {
  const data = await postJSON<ContextResponse>("/context/read", {
    context_dir: contextDir,
  });
  return data.context;
};

export const detectPattern = async (formText: string): Promise<string> => {
  const data = await postJSON<{ pattern: string }>("/pattern/detect", {
    text: formText,
    provider,
  });
  return data.pattern;
};

export const detectFillEntries = async (
  formText: string,
  keys: string[],
  pattern: string,
): Promise<FillEntry[]> => {
  const data = await postJSON<DetectFillEntriesResponse>(
    "/fill-entries/detect",
    {
      lines: formText.split("\n"),
      keys,
      pattern,
      provider,
    },
  );
  return data.entries;
};

export const processFillEntries = async (
  fillEntries: FillEntry[],
  contextDir: string,
  pattern: string,
): Promise<FillEntry[]> => {
  const data = await postJSON<DetectFillEntriesResponse>(
    "/fill-entries/process",
    {
      entries: fillEntries,
      context_dir: contextDir,
      pattern,
      provider,
    },
  );
  return data.entries;
};

export const detectCheckboxEntries = async (
  formText: string,
  keys: string[],
): Promise<CheckboxEntry[]> => {
  const data = await postJSON<{ entries: CheckboxEntry[] }>(
    "/checkbox-entries/detect",
    {
      lines: formText.split("\n"),
      keys,
    },
  );
  return data.entries;
};

export const processCheckboxEntries = async (
  checkboxEntries: CheckboxEntry[],
  contextDir: string,
  keys: string[],
): Promise<CheckboxEntry[]> => {
  const data = await postJSON<{ entries: CheckboxEntry[] }>(
    "/checkbox-entries/process",
    {
      entries: checkboxEntries,
      context_dir: contextDir,
      keys,
      provider,
    },
  );
  return data.entries;
};

export const fillForm = async (
  formPath: string,
  fillEntries: FillEntry[],
  checkboxEntries: CheckboxEntry[],
  outputPath: string,
): Promise<FillFormResponse> => {
  const url = formPath.toLowerCase().endsWith(".pdf") ? "/pdf/fill" : "/docx/fill";
  return postJSON<FillFormResponse>(url, {
    form_path: formPath,
    fill_entries: fillEntries,
    checkbox_entries: checkboxEntries,
    output_path: outputPath || null,
  });
};

export const extractContext = async (
  contextDir: string,
): Promise<Record<string, string | null>> => {
  const data = await postJSON<ContextResponse>("/context/extract", {
    context_dir: contextDir,
    provider,
  });
  return data.context;
};

export const getContextData = async (
  contextDir: string,
): Promise<Record<string, string> | null> => {
  const path = `${contextDir}/context_data.json`;
  const fileData = await window.fileContext.readFile(path);
  if (fileData && fileData.content) {
    const decodedContent = atob(fileData.content);
    return JSON.parse(decodedContent);
  }
  return null;
};

export const writeContextData = async (
  contextDir: string,
  contextData: Record<string, string>,
) => {
  const path = `${contextDir}/context_data.json`;
  const jsonContent = JSON.stringify(contextData, null, 2);
  const encodedContent = btoa(jsonContent);
  return window.fileContext.writeFile(path, encodedContent);
};

export const createBlobUrlFromContent = async (
  pdfPath: string,
  type: string,
): Promise<string> => {
  const fileData = await window.fileContext.readFile(pdfPath);
  const binaryData = atob(fileData.content);

  const byteArray = new Uint8Array(binaryData.length);
  for (let i = 0; i < binaryData.length; i++) {
    byteArray[i] = binaryData.charCodeAt(i);
  }

  const blob = new Blob([byteArray], { type });
  return URL.createObjectURL(blob);
};

export const previewFile = async (filePath: string) => {
  try {
    await window.helloWorldContext.openFile(filePath);
  } catch (error) {
    console.error("Error opening file:", error);
  }
};
