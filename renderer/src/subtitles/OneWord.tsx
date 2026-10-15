// Legenda OneWord: uma palavra por vez, grande, no centro da área segura.
import { textStyle } from "../text";
import type { SubtitleProps } from "../types";
import { SafeArea } from "./SafeArea";

export const OneWord: React.FC<SubtitleProps> = ({ line, current, font }) => {
  const word = line && current >= 0 ? line.words[current] : undefined;
  if (!word) return null;
  // estimativa conservadora: 0,8 em por letra, para a palavra caber em 920 px mesmo em maiúsculas
  const size = Math.min(180, Math.floor(920 / (word.text.length * 0.8)));
  return (
    <SafeArea>
      <div style={textStyle(font, size)}>{word.text}</div>
    </SafeArea>
  );
};
