// Movimento das legendas: entrada e saída do verso e pulso da palavra. Só tempo, sem Remotion, para ser testável.
import type { Line, Word } from "./types";

// Igual ao clamp01 de timing.ts; aqui para o teste rodar no node sem importar outro módulo com extensão .ts.
const clamp01 = (x: number): number => Math.min(1, Math.max(0, x));

const ENTER = 0.25; // segundos da entrada do verso
const EXIT = 0.25; // segundos da saída do verso, antes do fim
const POP = 0.18; // segundos do pulso da palavra atual
const POP_SIZE = 0.05; // shortcut: pico de 5% para o destaque caber no limite de 108% junto com o refrão

// 0 antes do verso, 1 depois de ENTER segundos, desacelerando no fim.
export const enterProgress = (t: number, line: Line): number => {
  const p = clamp01((t - line.start) / ENTER);
  return 1 - (1 - p) ** 3;
};

// 1 até faltar EXIT segundos para o fim do verso, depois cai até 0 no fim.
export const exitProgress = (t: number, line: Line): number => {
  const q = clamp01((line.end - t) / EXIT);
  return q * q;
};

// Escala da palavra: sobe e volta a 1 em POP segundos a partir do início dela.
export const wordPop = (t: number, word: Word): number => {
  const p = clamp01((t - word.start) / POP);
  return 1 + POP_SIZE * Math.sin(Math.PI * p);
};
