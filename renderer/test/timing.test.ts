// Self-check da legenda: linha ativa, tolerância de 0,5 s e palavra atual. Rode com npm test.
import { activeLine, activeWordIndex } from "../src/timing.ts";
import type { Line } from "../src/types.ts";

const line = (id: number, start: number, end: number, words: [string, number, number][]): Line => ({
  id,
  text: "",
  section: "verse",
  start,
  end,
  words: words.map(([text, s, e]) => ({ text, start: s, end: e })),
});

const lines: Line[] = [
  line(0, 1, 3, [["a", 1, 2], ["b", 2, 3]]),
  line(1, 5, 6, [["c", 5, 6]]),
];

const check = (ok: boolean, message: string) => {
  if (!ok) throw new Error(message);
};

check(activeLine(lines, 0.5) === null, "antes da primeira linha não há legenda");
check(activeLine(lines, 2)?.id === 0, "no meio da linha 0");
check(activeLine(lines, 3.4)?.id === 0, "até 0,5 s depois do fim ainda mostra");
check(activeLine(lines, 3.6) === null, "depois de 0,5 s sem linha ativa a legenda some");
check(activeLine(lines, 5.2)?.id === 1, "linha 1 começa");
check(activeWordIndex(lines[0], 0.5) === -1, "antes da primeira palavra não há destaque");
check(activeWordIndex(lines[0], 1.2) === 0, "palavra atual é a primeira");
check(activeWordIndex(lines[0], 2.5) === 1, "palavra atual é a segunda");

console.log("timing: ok");
