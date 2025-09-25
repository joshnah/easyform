import { read } from "fs";
import { FILE_CONTEXT, READ_API_KEYS_CHANNEL, READ_FILE_CHANNEL, WRITE_API_KEYS_CHANNEL, WRITE_FILE_CHANNEL } from "./file-channels";

export function exposeFileContext() {
  const { contextBridge, ipcRenderer } = window.require("electron");
  contextBridge.exposeInMainWorld(FILE_CONTEXT, {
    readFile: (path:string) => ipcRenderer.invoke(READ_FILE_CHANNEL, path),
    writeFile: (path:string, data:string | Buffer) => ipcRenderer.invoke(WRITE_FILE_CHANNEL, path, data),
    readApiKeys: () => ipcRenderer.invoke(READ_API_KEYS_CHANNEL),
    writeApiKeys: (data: any) => ipcRenderer.invoke(WRITE_API_KEYS_CHANNEL, data)
  });
}
