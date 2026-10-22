// Renderiza vários cortes numa só execução: um bundle para todos os cortes.
// Uso: npm run render-batch -- <manifesto.json> (lista de {props, video, finalProps, finalVideo}, ver engine/render.py)
// BROWSER_EXECUTABLE e RENDER_CONCURRENCY valem como no render.mjs.
import { readFile, rename } from "node:fs/promises";
import { resolve } from "node:path";
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";

const [manifestPath] = process.argv.slice(2);
if (!manifestPath) {
  console.error("uso: npm run render-batch -- <manifesto.json>");
  process.exit(1);
}
const manifest = JSON.parse(await readFile(manifestPath, "utf-8"));
const concurrency = process.env.RENDER_CONCURRENCY ? Number(process.env.RENDER_CONCURRENCY) : null;
const serveUrl = await bundle({ entryPoint: resolve("src/index.ts") });
const browserExecutable = process.env.BROWSER_EXECUTABLE || null;
// primeiro todos os trechos: o total de quadros do lote é o que a barra da web usa
const plan = [];
for (const job of manifest) {
  const inputProps = JSON.parse(await readFile(job.props, "utf-8"));
  const composition = await selectComposition({ serveUrl, id: "LyricVideo", inputProps, browserExecutable });
  plan.push({ ...job, inputProps, composition });
}
const total = plan.reduce((sum, job) => sum + job.composition.durationInFrames, 0);
let done = 0;
for (const job of plan) {
  // sem navegador compartilhado: cada render abre o seu, como o CLI (o compartilhado ficou mais lento na medição, ver docs/TESTES.md)
  await renderMedia({
    composition: job.composition,
    serveUrl,
    inputProps: job.inputProps,
    codec: "h264",
    // formato final já no render: a cópia para postar só remuxa, sem recodificar (engine/export.py)
    pixelFormat: "yuv420p",
    colorSpace: "bt709",
    crf: 23,
    encodingMaxRate: "8M",
    encodingBufferSize: "16M",
    audioBitrate: "128k",
    outputLocation: job.video,
    overwrite: true,
    browserExecutable,
    concurrency,
    onProgress: ({ renderedFrames }) => console.log(`Rendered ${done + renderedFrames}/${total}`),
  });
  done += job.composition.durationInFrames;
  // vídeo antes do props: se cair no meio, a próxima rodada refaz (mesma ordem de sempre)
  await rename(job.video, job.finalVideo);
  await rename(job.props, job.finalProps);
}
