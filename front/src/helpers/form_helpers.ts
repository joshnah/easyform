import { BACKEND_URL } from "@/const";


const DEFAULT_PROVIDER = "groq";
export const PROVIDERS = ["groq", "anythingllm", "local","openai"];


export let provider = DEFAULT_PROVIDER;

export const setProvider = (newProvider: string) => {
  provider = newProvider;
};

export const fetchFormText = async (formPath: string): Promise<string> => {
    const response = await fetch(`${BACKEND_URL}/form/text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ form_path: formPath }),
    });
    const data = await response.json();
    return data.text;
  };
  
  export const fetchContext = async (contextDir: string) => {
    const response = await fetch(`${BACKEND_URL}/context/read`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ context_dir: contextDir }),
    });
    const data = await response.json();
    return data.context;
  };
  
  export const detectPattern = async (formText: string) => {
    const response = await fetch(`${BACKEND_URL}/pattern/detect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: formText, provider }),
    });
    const data = await response.json();
    return data.pattern;
  };
  
  export const detectFillEntries = async (formText: string, keys: any, pattern: any )=> {
    const response = await fetch(`${BACKEND_URL}/fill-entries/detect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lines: formText.split('\n'), keys: keys, pattern, provider}),
    });
    const data = await response.json();
    return data.entries;
  };

  export const processFillEntries = async(fillEntries: any[], contextDir: string, pattern: string) => {
    const response = await fetch(`${BACKEND_URL}/fill-entries/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entries: fillEntries, context_dir: contextDir, pattern, provider}),
    });
    const data = await response.json();
    return data.entries;
  }

  export const detectCheckboxEntries = async (formText: string, keys: any) => {
    const response = await fetch(`${BACKEND_URL}/checkbox-entries/detect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lines: formText.split('\n'), keys }),
    });
    const data = await response.json();
    return data.entries;
  }

  export const processCheckboxEntries= async (checkboxEntries: any[], contextDir: string, keys: string[]) => {  
    const response = await fetch(`${BACKEND_URL}/checkbox-entries/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entries: checkboxEntries, context_dir: contextDir, keys, provider}),
    });
    const data = await response.json();
    return data.entries;
  }


  export const fillForm = async(formPath: string,fillEntries: any[], checkboxEntries: any[], outputPath: string) => {
    const url = formPath.endsWith('.pdf')? `${BACKEND_URL}/pdf/fill` : `${BACKEND_URL}/docs/fill`;
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ form_path: formPath, fill_entries: fillEntries, checkbox_entries: checkboxEntries, outputPath }),
    });
  }


  export const getContextData = async (contextDir: string) => {
    const path = `${contextDir}/context_data.json`;
    const fileData = await window.fileContext.readFile(path);
    if (fileData && fileData.content) {
      const decodedContent = atob(fileData.content);
      return JSON.parse(decodedContent);
    }
    return null;
  }

export const writeContextData = async (contextDir: string, contextData: any) => {
    const path = `${contextDir}/context_data.json`;
    const jsonContent = JSON.stringify(contextData, null, 2);
    const encodedContent = btoa(jsonContent);
    return window.fileContext.writeFile(path, encodedContent);
  };

  export const createBlobUrlFromContent = async (pdfPath: string, type: string): Promise<string> => {
    const fileData = await window.fileContext.readFile(
      pdfPath
    );

    const binaryData = atob(fileData.content);
  
    // Convert binary data to a Uint8Array
    const byteArray = new Uint8Array(binaryData.length);
    for (let i = 0; i < binaryData.length; i++) {
      byteArray[i] = binaryData.charCodeAt(i);
    }
  
    // Create a Blob from the Uint8Array
    const blob = new Blob([byteArray], { type });
  
    // Generate a Blob URL
    return URL.createObjectURL(blob);
  };

  export const previewFile = async (filePath: string) => {
    try {
      await window.helloWorldContext.openFile(filePath);
    } catch (error) {
      console.error('Error opening file:', error);
    }
  };

  export const extractContext = async (contextDir:string)=> {
    const response = await fetch(`${BACKEND_URL}/context/extract`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ context_dir: contextDir, provider}),
    });
    const data = await response.json();
    return data.context;
  }