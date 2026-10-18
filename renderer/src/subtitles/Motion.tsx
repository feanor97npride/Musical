// Envolve a legenda: entra subindo e aumentando, sai desvanecendo, e cresce um pouco no refrão.
import { enterProgress, exitProgress } from "../motion";
import type { Line } from "../types";

type Props = { line: Line | null; t: number; intensity: number; children: React.ReactNode };

export const Motion: React.FC<Props> = ({ line, t, intensity, children }) => {
  const enter = line ? enterProgress(t, line) : 0;
  const exit = line ? exitProgress(t, line) : 0;
  const scale = (0.92 + 0.08 * enter) * (1 + 0.03 * intensity); // refrão: 3% maior, para caber no limite de 108%
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        opacity: Math.min(enter, exit),
        transform: `translateY(${40 * (1 - enter)}px) scale(${scale})`,
      }}
    >
      {children}
    </div>
  );
};
