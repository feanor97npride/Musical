// Self-check do zoom da imagem de fundo: começa em 1, termina em 1,08 e cresce sempre. Rode com npm test.
import { zoomAt } from "../src/image.ts";

const check = (ok: boolean, message: string) => {
  if (!ok) throw new Error(message);
};
const close = (a: number, b: number) => Math.abs(a - b) < 1e-9;

check(close(zoomAt(0, 300), 1), "zoom deve começar em 1");
check(close(zoomAt(300, 300), 1.08), "zoom deve terminar em 1,08");
check(close(zoomAt(-5, 300), 1) && close(zoomAt(900, 300), 1.08), "frame fora do vídeo deve ser cortado");
check(zoomAt(10, 300) < zoomAt(150, 300) && zoomAt(150, 300) < zoomAt(290, 300), "zoom deve crescer sempre");
check(Number.isFinite(zoomAt(0, 0)), "duração zero não pode dar NaN");
