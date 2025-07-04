import React from "react";
import ToggleTheme from "@/components/ToggleTheme";
import InitialIcons from "@/components/template/InitialIcons";
import { DialogDemo } from "@/components/x/DialogDemo";
import { Button } from "@/components/ui/button";

export default function XPage() {
  const [log, setLog] = React.useState<string>("");

  return (
    <div className="flex h-full flex-col">
      log: {log}
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
      </div>
    </div>
  );
}
