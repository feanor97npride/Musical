// Self-check do movimento das legendas: entrada, saída e pulso da palavra. Rode com npm test.
import { enterProgress, exitProgress, wordPop } from "../src/motion.ts";
import type { Line, Word } from "../src/types.ts";

const check = (ok: boolean, message: string) => {
  if (!ok) throw new Error(message);
};
const close = (a: number, b: number) => Math.abs(a - b) < 1e-6;

const line: Line = { id: 0, text: "", section: "verse", start: 10, end: 12, words: [{ text: "a", start: 10, end: 11 }] };
const word: Word = { text: "a", start: 10, end: 11 };

check(enterProgress(9.5, line) === 0, "antes do verso a entrada é 0");
check(close(enterProgress(10.25, line), 1), "0,25 s depois do início a entrada é 1");
check(enterProgress(10.1, line) > enterProgress(10.05, line), "a entrada cresce com o tempo");

check(close(exitProgress(11.75, line), 1), "até 0,25 s antes do fim a saída é 1");
check(close(exitProgress(12, line), 0), "no fim do verso a saída é 0");
check(exitProgress(11.9, line) > exitProgress(11.95, line), "a saída diminui com o tempo");

check(close(wordPop(10, word), 1), "no início da palavra o pulso é 1");
check(close(wordPop(10.09, word), 1.05), "no meio do pulso a escala é 1,05");
check(close(wordPop(10.5, word), 1), "depois do pulso a escala volta a 1");

console.log("motion: ok");
