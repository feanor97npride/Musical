// Self-check do tamanho da legenda: palavra curta fica no tamanho base, palavra longa encolhe até caber. Rode com npm test.
import { fitSize } from "../src/fit.ts";

const check = (ok: boolean, message: string) => {
  if (!ok) throw new Error(message);
};

check(fitSize(["oi"], 88, 1080) === 88, "palavra curta deve ficar no tamanho base");
check(fitSize([], 88, 1080) === 88, "sem palavras deve ficar no tamanho base");
const longa = fitSize(["a".repeat(20)], 88, 1080);
check(longa < 88 && longa > 0, "palavra de 20 letras deve encolher");
check(longa * 0.8 * 20 <= 1080 - 160, "palavra de 20 letras deve caber na área segura");
check(fitSize(["a"], 88, 5000) === 88, "nunca passa do tamanho base");
check(fitSize(["a".repeat(14), "oi"], 88, 1080) < 88, "a palavra mais longa da linha define o tamanho");
