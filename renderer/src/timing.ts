// Linha ativa, palavra atual, pulso e intensidade do refrão em um instante. Sem Remotion, para ser testável.
import type { Line } from "./types";

const GAP_LIMIT = 0.5; // segundos sem linha ativa até a legenda sumir
const CHORUS_RAMP = 0.6; // segundos para o efeito do refrão entrar e sair sem salto

export const clamp01 = (x: number): number => Math.min(1, Math.max(0, x));

// Linha que contém t. Se nenhuma contém, a última que começou, até GAP_LIMIT depois do fim.
export const activeLine = (lines: Line[], t: number): Line | null => {
  let started: Line | null = null;
  let containing: Line | null = null;
  for (const line of lines) {
    if (line.start > t) break;
    started = line;
    if (t <= line.end) containing = line;
  }
  if (containing) return containing;
  return started && t <= started.end + GAP_LIMIT ? started : null;
};

// Índice da última palavra que já começou em t; -1 antes da primeira.
export const activeWordIndex = (line: Line, t: number): number =>
  line.words.reduce((last, word, index) => (word.start <= t ? index : last), -1);

// Pulso da batida: pico de 3% na batida e decai depois dela. Usa as batidas reais (em segundos) quando existem;
// sem elas, cai na grade de batida pelo bpm, contada desde o tempo zero.
export const beatPulse = (t: number, bpm: number, beats: number[] = []): number => {
  if (beats.length > 0) {
    let last = -Infinity;
    for (const beat of beats) {
      if (beat > t) break;
      last = beat;
    }
    return last === -Infinity ? 0 : 0.03 * Math.exp(-(t - last) * 8);
  }
  if (bpm <= 0) return 0;
  const beat = ((t * bpm) / 60) % 1;
  return 0.03 * Math.exp(-beat * 8);
};

// Intensidade do refrão em t: 1 dentro de um verso de refrão, cai para 0 em CHORUS_RAMP segundos.
export const chorusWeight = (lines: Line[], t: number): number => {
  let nearest = Infinity;
  for (const line of lines) {
    if (line.section !== "chorus") continue;
    const distance = t < line.start ? line.start - t : t > line.end ? t - line.end : 0;
    nearest = Math.min(nearest, distance);
  }
  return nearest === Infinity ? 0 : clamp01(1 - nearest / CHORUS_RAMP);
};

// Fator de brilho do fundo: sobe com o pulso da batida e com a intensidade do refrão.
export const lightFactor = (pulse: number, intensity: number): number => (1 + pulse) * (1 + 0.12 * intensity);
