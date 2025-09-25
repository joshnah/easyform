import { exposeFileContext } from "./file/file-context";
import { exposeThemeContext } from "./theme/theme-context";
import { exposeWindowContext } from "./window/window-context";
import { exposeHelloWorldContext } from "./x/hello/hello-world-context";

export default function exposeContexts() {
  exposeWindowContext();
  exposeThemeContext();
  exposeHelloWorldContext();
  exposeFileContext();
}
