// Legenda Karaoke: o verso inteiro, com a cor avançando dentro de cada palavra.
import { Fragment } from "react";
import { useVideoConfig } from "remotion";
import { fitSize } from "../fit";
import { HIGHLIGHT, SHADOW, textStyle } from "../text";
import { clamp01 } from "../timing";
import type { SubtitleProps } from "../types";
import { SafeArea } from "./SafeArea";

// O espaço entre as palavras é o que deixa o navegador quebrar a linha.
// A sombra fica no pai, num filtro só: um filtro por palavra custa caro no render.
export const Karaoke: React.FC<SubtitleProps> = ({ line, current, t, font }) => {
  const { width } = useVideoConfig();
  if (!line) return null;
  const size = fitSize(line.words.map((word) => word.text), 88, width);
  return (
    <SafeArea>
      <div style={{ ...textStyle(font, size), textShadow: "none", filter: SHADOW }}>
        {line.words.map((word, index) => {
          const progress =
            index < current ? 1 : index === current ? clamp01((t - word.start) / Math.max(word.end - word.start, 0.01)) : 0;
          const edge = `${progress * 100}%`;
          return (
            <Fragment key={index}>
              {index > 0 && " "}
              <span
                style={{
                  color: "transparent",
                  backgroundImage: `linear-gradient(90deg, ${HIGHLIGHT} ${edge}, #FFFFFF ${edge})`,
                  WebkitBackgroundClip: "text",
                  backgroundClip: "text",
                }}
              >
                {word.text}
              </span>
            </Fragment>
          );
        })}
      </div>
    </SafeArea>
  );
};
