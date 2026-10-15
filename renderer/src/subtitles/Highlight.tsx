// Legenda Highlight: o verso inteiro na tela, com a palavra atual em destaque.
import { Fragment } from "react";
import { HIGHLIGHT, textStyle } from "../text";
import type { SubtitleProps } from "../types";
import { SafeArea } from "./SafeArea";

// O espaço entre as palavras é o que deixa o navegador quebrar a linha.
export const Highlight: React.FC<SubtitleProps> = ({ line, current, font }) => {
  if (!line) return null;
  return (
    <SafeArea>
      <div style={textStyle(font, 88)}>
        {line.words.map((word, index) => (
          <Fragment key={index}>
            {index > 0 && " "}
            <span style={{ color: index === current ? HIGHLIGHT : "#FFFFFF" }}>{word.text}</span>
          </Fragment>
        ))}
      </div>
    </SafeArea>
  );
};
