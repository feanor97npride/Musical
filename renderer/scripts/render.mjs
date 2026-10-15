// Renderiza a composição LyricVideo: npm run render -- <props.json> <saida.mp4>
// BROWSER_EXECUTABLE (opcional) aponta para um Chrome/headless shell já instalado.
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

const [props, output] = process.argv.slice(2);
if (!props || !output) {
  console.error("uso: npm run render -- <props.json> <saida.mp4>");
  process.exit(1);
}
const browser = process.env.BROWSER_EXECUTABLE ? ["--browser-executable", process.env.BROWSER_EXECUTABLE] : [];
execFileSync(
  "npx",
  ["remotion", "render", "src/index.ts", "LyricVideo", resolve(output), "--props", resolve(props), ...browser],
  { stdio: "inherit" },
);
