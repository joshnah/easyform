import { BrowserWindow } from "electron";
import { addThemeEventListeners } from "./theme/theme-listeners";
import { addWindowEventListeners } from "./window/window-listeners";
import { helloWorldListener } from "@/helpers/ipc/x/hello/hello-world-listener";
import { FileListener } from "./file/file-listener";

export default function registerListeners(mainWindow: BrowserWindow) {
  addWindowEventListeners(mainWindow);
  addThemeEventListeners();
  helloWorldListener();
  FileListener();
}
