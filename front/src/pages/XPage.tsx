import React from "react";
// import ToggleTheme from "@/components/ToggleTheme";
import InitialIcons from "@/components/template/InitialIcons";
import { DialogDemo } from "@/components/x/DialogDemo";
import { Button } from "@/components/ui/button";

export default function XPage() {
  const [log, setLog] = React.useState<string>("");
  const [filePath, setFilePath] = React.useState<string | null>(null);
  const [dirPath, setDirPath] = React.useState<string | undefined>(undefined);

  return (
    <div className="flex h-full flex-col">
      log: {log}
      <br />
      filePath: {filePath}
      <br />
      dirPath: {dirPath}
      <div className="flex flex-1 flex-col items-center justify-center gap-2">
        <InitialIcons />
        <DialogDemo />
        {/* <ToggleTheme /> */}
        <Button onClick={
          async () => await window.helloWorldContext.helloWorld()
        }>
          Hello World
        </Button>
        <Button onClick={
          async () => await window.helloWorldContext.createFile("Hello World!")
        }>
          Create File
        </Button>
        <Button onClick={
          async () => {
            const stdout = await window.helloWorldContext.runBashScript()
            setLog(stdout);
          }
        }>
          Run Bash Script
        </Button>
        <Button onClick={
          async () => {
            const stdout = await window.helloWorldContext.runBin()
            setLog(stdout);
          }
        }>
          Run Python Binary
        </Button>
        <Button onClick={
          async () => {
            const path = await window.helloWorldContext.selectFile()
            setFilePath(path);
          }
        }>
          Get Absolute File Path
        </Button>
        <Button onClick={
          async () => {
            if (filePath !== null) {
              await window.helloWorldContext.openFile(filePath);
            }
          }
        }>
          Preview file
        </Button>
        <Button onClick={
          async () => {
            const dir = await window.helloWorldContext.selectDirectory()
            setDirPath(dir?.path);
            console.dir(dir);
          }
        }>
          Select Directory
        </Button>
      </div>
    </div>
  );
}
