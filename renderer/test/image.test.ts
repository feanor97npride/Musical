// Self-check da animação da imagem: começa sem deslocamento, termina em zoom 1,08 e o deslocamento fica dentro da folga. Rode com npm test.
import { transformAt } from "../src/image.ts";

const check = (ok: boolean, message: string) => {
  if (!ok) throw new Error(message);
};
const close = (a: number, b: number) => Math.abs(a - b) < 1e-9;

const start = transformAt(0, 300);
check(close(start.scale, 1) && close(start.x, 0) && close(start.y, 1.5), "início: zoom 1 e deslocamento inicial");
check(close(transformAt(300, 300).scale, 1.08), "fim: zoom 1,08");
check(close(transformAt(-5, 300).scale, 1) && close(transformAt(900, 300).scale, 1.08), "frame fora do vídeo deve ser cortado");
check(transformAt(10, 300).scale < transformAt(150, 300).scale && transformAt(150, 300).scale < transformAt(290, 300).scale,
  "zoom deve crescer sempre");
for (let frame = 0; frame <= 300; frame += 10) {
  const t = transformAt(frame, 300);
  check(Math.abs(t.x) <= 2.5 + 1e-9 && Math.abs(t.y) <= 1.5 + 1e-9, `deslocamento fora da folga no frame ${frame}`);
}
check(Number.isFinite(transformAt(0, 0).scale), "duração zero não pode dar NaN");
