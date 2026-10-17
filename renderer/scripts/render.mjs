// Renderiza a composição LyricVideo: npm run render -- <props.json> <saida.mp4>
// BROWSER_EXECUTABLE (opcional) aponta para um Chrome/headless shell já instalado.
// RENDER_CONCURRENCY (opcional) número de processos de render; vazio = padrão do Remotion.
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const [props, output] = process.argv.slice(2);
if (!props || !output) {
  console.error("uso: npm run render -- <props.json> <saida.mp4>");
  process.exit(1);
}
// chama o CLI do Remotion pelo próprio Node: igual no Windows e no Linux, sem passar pelo shell
const cli = fileURLToPath(new URL("../node_modules/@remotion/cli/remotion-cli.js", import.meta.url));
const browser = process.env.BROWSER_EXECUTABLE ? ["--browser-executable", process.env.BROWSER_EXECUTABLE] : [];
const concurrency = process.env.RENDER_CONCURRENCY ? ["--concurrency", process.env.RENDER_CONCURRENCY] : [];
execFileSync(
  process.execPath,
  [cli, "render", "src/index.ts", "LyricVideo", resolve(output), "--props", resolve(props), ...browser, ...concurrency],
  { stdio: "inherit" },
);
