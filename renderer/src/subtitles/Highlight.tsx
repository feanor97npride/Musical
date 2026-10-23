// Legenda Highlight: o verso inteiro na tela, com a palavra atual em destaque.
import { Fragment } from "react";
import { useVideoConfig } from "remotion";
import { fitSize } from "../fit";
import { wordPop } from "../motion";
import { HIGHLIGHT, textStyle } from "../text";
import type { SubtitleProps } from "../types";
import { SafeArea } from "./SafeArea";

// O espaço entre as palavras é o que deixa o navegador quebrar a linha.
export const Highlight: React.FC<SubtitleProps> = ({ line, current, t, font }) => {
  const { width } = useVideoConfig();
  if (!line) return null;
  return (
    <SafeArea>
      <div style={textStyle(font, fitSize(line.words.map((word) => word.text), 88, width))}>
        {line.words.map((word, index) => (
          <Fragment key={index}>
            {index > 0 && " "}
            <span
              style={{
                color: index === current ? HIGHLIGHT : "#FFFFFF",
                display: "inline-block",
                transform: `scale(${index === current ? wordPop(t, word) : 1})`,
              }}
            >
              {word.text}
            </span>
          </Fragment>
        ))}
      </div>
    </SafeArea>
  );
};
