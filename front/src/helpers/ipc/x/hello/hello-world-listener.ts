import { ipcMain, IpcMainInvokeEvent } from "electron";
import { writeFile } from "fs/promises";
import { join } from "path";
import { app } from "electron";
import path from 'path';
import { promisify } from 'util';
import { exec } from 'child_process';
import {
  HELLO_WORLD_CHANNEL,
  CREATE_FILE_CHANNEL,
  RUN_BASH_SCRIPT_CHANNEL,
  RUN_BIN_CHANNEL,
} from "./hello-world-channels";

const execAsync = promisify(exec);

export function helloWorldListener() {
  ipcMain.handle(HELLO_WORLD_CHANNEL,
    () => {
      console.log("Hello, World!")
      console.log(__dirname);
    }
  );
  ipcMain.handle(CREATE_FILE_CHANNEL, async (_event: IpcMainInvokeEvent, content: string) => {
    // console.log(_event);
    try {
      // Hard-coded file name for demo
      const fileName = "demo-file.txt";

      // Get the user's documents directory or app data directory
      const userDataPath = app.getPath('userData');
      const filePath = join(userDataPath, fileName);

      // Create the file with the provided content
      await writeFile(filePath, content, 'utf8');

      console.log(`File created successfully: ${filePath}`);
      return {
        success: true,
        message: `File '${fileName}' created successfully`,
        path: filePath
      };
    } catch (error: any) {
      console.error('Error creating file:', error);
      return {
        success: false,
        message: `Failed to create file: ${error.message}`,
        error: error.message
      };
    }
  });

  ipcMain.handle(RUN_BASH_SCRIPT_CHANNEL, async () => {
    let scriptPath: string;
    if (app.isPackaged) {
      scriptPath = path.join(process.resourcesPath, 'assets', 'helloworld.sh');
    } else {
      scriptPath = path.join(app.getAppPath(), 'src/assets', 'helloworld.sh');
    }

    console.log(`Running bash script: ${scriptPath}`);

    const fs = require('fs');
    if (!fs.existsSync(scriptPath)) {
      console.error(`Script not found at: ${scriptPath}`);
      throw new Error(`Script not found at: ${scriptPath}`);
    }

    try {
      const { stdout, stderr } = await execAsync(`bash "${scriptPath}"`);

      if (stderr) {
        console.error('Script stderr:', stderr);
        // Note: stderr doesn't always mean error, some programs output to stderr
      }

      console.log('Script stdout:', stdout);
      return stdout.trim(); // trim to remove trailing newlines
    } catch (error) {
      console.error('Execution error:', error);
      throw error;
    }
  });

  ipcMain.handle(RUN_BIN_CHANNEL, async () => {
    let scriptPath: string;
    if (app.isPackaged) {
      scriptPath = path.join(process.resourcesPath, 'assets/python', 'helloworld');
    } else {
      scriptPath = path.join(app.getAppPath(), 'src/assets/python', 'helloworld');
    }

    console.log(`Running bash script: ${scriptPath}`);

    const fs = require('fs');
    if (!fs.existsSync(scriptPath)) {
      console.error(`Script not found at: ${scriptPath}`);
      throw new Error(`Script not found at: ${scriptPath}`);
    }

    try {
      // const { stdout, stderr } = await execAsync(`bash "${scriptPath}"`);
      const { stdout, stderr } = await execAsync(`${scriptPath}`);

      if (stderr) {
        console.error('Script stderr:', stderr);
        // Note: stderr doesn't always mean error, some programs output to stderr
      }

      console.log('Script stdout:', stdout);
      return stdout.trim(); // trim to remove trailing newlines
    } catch (error) {
      console.error('Execution error:', error);
      throw error;
    }
  });
}
