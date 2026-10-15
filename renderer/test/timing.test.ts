// Self-check da legenda, do refrão e do pulso: linha ativa, tolerância, palavra atual, rampa do refrão e brilho. Rode com npm test.
import { activeLine, activeWordIndex, beatPulse, chorusWeight, clamp01, lightFactor } from "../src/timing.ts";
import type { Line, Section } from "../src/types.ts";

const line = (id: number, start: number, end: number, words: [string, number, number][], section: Section = "verse"): Line => ({
  id,
  text: "",
  section,
  start,
  end,
  words: words.map(([text, s, e]) => ({ text, start: s, end: e })),
});

const lines: Line[] = [
  line(0, 1, 3, [["a", 1, 2], ["b", 2, 3]]),
  line(1, 5, 6, [["c", 5, 6]]),
];

// linha 1 começa antes da 0 terminar: a que contém o instante deve ganhar
const overlapping: Line[] = [line(0, 1, 10, [["a", 1, 2]]), line(1, 3, 4, [["b", 3, 4]])];

const check = (ok: boolean, message: string) => {
  if (!ok) throw new Error(message);
};
const close = (a: number, b: number) => Math.abs(a - b) < 1e-6;

check(activeLine(lines, 0.5) === null, "antes da primeira linha não há legenda");
check(activeLine(lines, 2)?.id === 0, "no meio da linha 0");
check(activeLine(lines, 3.4)?.id === 0, "até 0,5 s depois do fim ainda mostra");
check(activeLine(lines, 3.6) === null, "depois de 0,5 s sem linha ativa a legenda some");
check(activeLine(lines, 5.2)?.id === 1, "linha 1 começa");
check(activeLine(overlapping, 6)?.id === 0, "linha que ainda contém o instante não some");
check(activeWordIndex(lines[0], 0.5) === -1, "antes da primeira palavra não há destaque");
check(activeWordIndex(lines[0], 1.2) === 0, "palavra atual é a primeira");
check(activeWordIndex(lines[0], 2.5) === 1, "palavra atual é a segunda");

check(close(beatPulse(0, 120), 0.03), "pulso no tempo da batida é 3%");
check(beatPulse(0.25, 120) < 0.001, "meio tempo depois da batida o pulso já decaiu");
check(beatPulse(1, 0) === 0, "sem bpm não há pulso");
check(clamp01(1.5) === 1 && clamp01(-1) === 0, "clamp01 limita entre 0 e 1");

// refrão: entra e sai em rampa de 0,6 s, sem salto
const song: Line[] = [
  line(0, 5, 8, [["x", 5, 8]], "chorus"),
  line(1, 9, 12, [["y", 9, 12]], "verse"),
];
check(chorusWeight(song, 6.5) === 1, "dentro do refrão a intensidade é 1");
check(close(chorusWeight(song, 8.3), 0.5), "0,3 s depois do refrão a intensidade é metade");
check(close(chorusWeight(song, 4.7), 0.5), "0,3 s antes do refrão a intensidade é metade");
check(chorusWeight(song, 9) === 0, "fora da rampa a intensidade é 0");
check(chorusWeight([], 6) === 0, "sem refrão a intensidade é 0");

check(lightFactor(0, 0) === 1, "sem pulso e sem refrão o brilho é 1");
check(close(lightFactor(0.03, 1), 1.03 * 1.12), "pulso e refrão somam no brilho");

console.log("timing: ok");
