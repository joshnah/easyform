import { app, ipcMain, IpcMainInvokeEvent } from "electron";
import { READ_API_KEYS_CHANNEL, READ_FILE_CHANNEL, WRITE_API_KEYS_CHANNEL, WRITE_FILE_CHANNEL } from "./file-channels";
import path from "path";
import fs from "fs";

const API_KEY_FILE = path.join(app.getPath('userData'), 'api_keys.json');
console.log("API Key file path:", API_KEY_FILE);

export function FileListener() {
  ipcMain.handle(READ_FILE_CHANNEL, async (_event: IpcMainInvokeEvent, filePath: string) => {
    try {
      const fs = require('fs/promises');
      const fileBuffer = await fs.readFile(filePath);
  
      return {
        content: fileBuffer.toString("base64"), // Convert to base64 for transport
      };
    } catch (error) {
      console.error("Error reading PDF file:", error);
      throw error;
    }
  });
  
 // Handler for writing a file
  ipcMain.handle(WRITE_FILE_CHANNEL, async (_event: IpcMainInvokeEvent, filePath: string, data: string | Buffer) => {
    try {
      const fs = require('fs/promises');
      // If data is base64 string, decode it
      const buffer = typeof data === "string" ? Buffer.from(data, "base64") : data;
      await fs.writeFile(filePath, buffer);
      return { success: true };
    } catch (error) {
      console.error("Error writing file:", error);
      throw error;
    }
  })

  ipcMain.handle(READ_API_KEYS_CHANNEL, async () => {
    try {
      if (fs.existsSync(API_KEY_FILE)) {
        const data = fs.readFileSync(API_KEY_FILE, "utf-8");
        return JSON.parse(data);
      }
      return [];
    } catch (error) {
      console.error("Failed to read API keys:", error);
      throw error;
    }
  });

  ipcMain.handle(WRITE_API_KEYS_CHANNEL, async (_, keys) => {
    try {
      // Ensure the directory exists before writing
      const dir = path.dirname(API_KEY_FILE);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
      fs.writeFileSync(API_KEY_FILE, JSON.stringify(keys, null, 2), "utf-8");
    } catch (error) {
      console.error("Failed to write API keys:", error);
      throw error;
    }
  });
}
