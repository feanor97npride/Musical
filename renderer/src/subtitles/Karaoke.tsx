// Legenda Karaoke: o verso inteiro, com a cor avançando dentro de cada palavra.
import { Fragment } from "react";
import { HIGHLIGHT, SHADOW, textStyle } from "../text";
import { clamp01 } from "../timing";
import type { SubtitleProps } from "../types";
import { SafeArea } from "./SafeArea";

// O espaço entre as palavras é o que deixa o navegador quebrar a linha.
export const Karaoke: React.FC<SubtitleProps> = ({ line, current, t, font }) => {
  if (!line) return null;
  return (
    <SafeArea>
      <div style={{ ...textStyle(font, 88), textShadow: "none" }}>
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
                  filter: SHADOW,
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
