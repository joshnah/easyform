import { HELLO_WORLD_CHANNEL, CONTEXT, CREATE_FILE_CHANNEL, RUN_BASH_SCRIPT_CHANNEL, RUN_BIN_CHANNEL } from "./hello-world-channels";

export function exposeHelloWorldContext() {
  const { contextBridge, ipcRenderer } = window.require("electron");
  contextBridge.exposeInMainWorld(CONTEXT, {
    helloWorld: () => ipcRenderer.invoke(HELLO_WORLD_CHANNEL),
    createFile: (content: string) => ipcRenderer.invoke(CREATE_FILE_CHANNEL, content),
    runBashScript: (content: string) => ipcRenderer.invoke(RUN_BASH_SCRIPT_CHANNEL),
    runBin: (content: string) => ipcRenderer.invoke(RUN_BIN_CHANNEL),
  });
}
