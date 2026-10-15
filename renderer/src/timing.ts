// Linha ativa e palavra atual em um instante. Sem Remotion, para ser testável.
import type { Line } from "./types";

const GAP_LIMIT = 0.5; // segundos sem linha ativa até a legenda sumir

// Última linha que já começou em t. Depois do fim dela, a legenda fica até GAP_LIMIT.
export const activeLine = (lines: Line[], t: number): Line | null => {
  let found: Line | null = null;
  for (const line of lines) {
    if (line.start > t) break;
    found = line;
  }
  return found && t <= found.end + GAP_LIMIT ? found : null;
};

// Índice da última palavra que já começou em t; -1 antes da primeira.
export const activeWordIndex = (line: Line, t: number): number =>
  line.words.reduce((last, word, index) => (word.start <= t ? index : last), -1);
