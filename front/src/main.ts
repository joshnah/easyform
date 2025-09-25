import { app, BrowserWindow } from "electron";
import registerListeners from "./helpers/ipc/listeners-register";
// "electron-squirrel-startup" seems broken when packaging with vite
//import started from "electron-squirrel-startup";
import path from 'path';
let backend: any = null;

import {
  installExtension,
  REACT_DEVELOPER_TOOLS,
} from "electron-devtools-installer";

const { execSync } = require('child_process');

const inDevelopment = process.env.NODE_ENV === "development";

function createWindow() {
  console.log("Creating window ...")
  const preload = path.join(__dirname, "preload.js");
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 900,
    webPreferences: {
      devTools: inDevelopment,
      contextIsolation: true,
      nodeIntegration: true,
      nodeIntegrationInSubFrames: false,

      preload: preload,
    },
  });

  // Start backend
  if (!inDevelopment || app.isPackaged) {
    console.log("Starting backend ...")
    let scriptPath: string;
    let userBackendDir = path.join(app.getPath('userData'), 'backend');
    let userBackendExe = path.join(userBackendDir, 'server.exe');
    console.log("User backend path:", userBackendExe);
    let packagedBackendDir: string;
    if (app.isPackaged) {
      packagedBackendDir = path.join(app.getAppPath(), '../../backend');
    } else {
      packagedBackendDir = path.join(app.getAppPath(), '../backend');
    }
    console.log("Packaged backend dir:", packagedBackendDir);
    const fs = require('fs');
    function copyDirSync(src: string, dest: string) {
      if (!fs.existsSync(dest)) {
      fs.mkdirSync(dest, { recursive: true });
      }
      const entries = fs.readdirSync(src, { withFileTypes: true });
      for (const entry of entries) {
      const srcPath = path.join(src, entry.name);
      const destPath = path.join(dest, entry.name);
      if (entry.isDirectory()) {
        copyDirSync(srcPath, destPath);
      } else {
        fs.copyFileSync(srcPath, destPath);
      }
      }
    }

    if (!fs.existsSync(userBackendExe)) {
      console.log('Copying backend folder to user data directory...');
      copyDirSync(packagedBackendDir, userBackendDir);
    }
    scriptPath = userBackendExe;

    console.log(`Running backend: ${scriptPath}`);

    if (!fs.existsSync(scriptPath)) {
      console.error(`Script not found at: ${scriptPath}`);
      throw new Error(`Script not found at: ${scriptPath}`);
    }

    try {
      const { spawn } = require('child_process');
      backend = spawn(`"${scriptPath}"`, [], { shell: true });

      backend.stdout.on('data', (data: Buffer) => {
        console.log(`[backend stdout]: ${data.toString()}`);
      });

      backend.stderr.on('data', (data: Buffer) => {
        console.error(`[backend stderr]: ${data.toString()}`);
      });

      backend.on('close', (code: number) => {
        console.log(`Backend process exited with code ${code}`);
      });

      console.log("Server process started");
    } catch (error) {
      console.error('Execution error:', error);
      throw error;
    }
  }
  // Kill backend process when Electron app quits
  app.on("quit", () => {
    if (backend) {
      console.log("Killing backend process...");
      try {
        // Try to gracefully terminate the backend process
        backend.kill();
        // If still running, force kill
        if (!backend.killed) {
          backend.kill('SIGKILL');
        }
      } catch (err) {
        console.error("Error killing backend process:", err);
      }
    }
    // Force kill any process using port 8000 (Windows only)
    try {
      execSync('powershell -Command "Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force"', { stdio: 'ignore' });
      console.log("Force killed process on port 8000.");
    } catch (err) {
      console.error("Error force killing process on port 8000:", err);
    }
  });
  process.on('SIGINT', () => {
    app.quit();
    backend.kill();

  });
  process.on('SIGTERM', () => {
    app.quit();
    backend.kill();
  });

  // Rerender electron window
  registerListeners(mainWindow);
  mainWindow.webContents.openDevTools({ mode: 'detach' });

  if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(MAIN_WINDOW_VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(
      path.join(__dirname, `../renderer/${MAIN_WINDOW_VITE_NAME}/index.html`),
    );
  }
}

async function installExtensions() {
  try {
    const result = await installExtension(REACT_DEVELOPER_TOOLS);
    console.log(`Extensions installed successfully: ${result.name}`);
  } catch {
    console.error("Failed to install extensions");
  }
}

app.whenReady().then(createWindow).then(installExtensions);

//osX only
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
//osX only ends
