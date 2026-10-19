// Self-check do sol: começa no horizonte, termina no alto e sobe sempre entre os dois. Rode com npm test.
import { sunHeight } from "../src/sun.ts";

const check = (ok: boolean, message: string) => {
  if (!ok) throw new Error(message);
};
const close = (a: number, b: number) => Math.abs(a - b) < 1e-6;

check(close(sunHeight(0), 0), "sol deve começar no horizonte");
check(close(sunHeight(1), 1), "sol deve terminar no alto");
check(close(sunHeight(-1), 0) && close(sunHeight(2), 1), "progresso fora de 0 a 1 deve ser cortado");
check(sunHeight(0.25) < sunHeight(0.5) && sunHeight(0.5) < sunHeight(0.75), "sol deve subir sempre");
console.log("sun: ok");
