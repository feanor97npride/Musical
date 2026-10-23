// Legenda OneWord: uma palavra por vez, grande, no centro da área segura.
import { useVideoConfig } from "remotion";
import { fitSize } from "../fit";
import { wordPop } from "../motion";
import { textStyle } from "../text";
import type { SubtitleProps } from "../types";
import { SafeArea } from "./SafeArea";

export const OneWord: React.FC<SubtitleProps> = ({ line, current, t, font }) => {
  const { width } = useVideoConfig();
  const word = line && current >= 0 ? line.words[current] : undefined;
  if (!word) return null;
  const size = fitSize([word.text], 180, width);
  return (
    <SafeArea>
      <div style={{ ...textStyle(font, size), transform: `scale(${wordPop(t, word)})` }}>{word.text}</div>
    </SafeArea>
  );
};
