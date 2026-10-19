// Sol nascendo: céu em degradê com a paleta, sol subindo no horizonte e halo que acompanha a batida e o refrão.
// shortcut: desenho em Canvas 2D a cada quadro; custo ainda não medido, medir antes de usar em muitas músicas.
import { useLayoutEffect, useRef } from "react";
import { AbsoluteFill, useVideoConfig } from "remotion";
import { sunHeight } from "../sun";

export const Sunrise: React.FC<{ palette: string[]; intensity: number; pulse: number; progress: number }> = ({
  palette,
  intensity,
  pulse,
  progress,
}) => {
  const { width, height } = useVideoConfig();
  const canvas = useRef<HTMLCanvasElement>(null);

  // desenha no commit do quadro, antes da captura; só usa progress, pulse e intensity, então o mesmo quadro sai igual
  useLayoutEffect(() => {
    const ctx = canvas.current?.getContext("2d");
    if (!ctx) return;
    const horizon = height * 0.62;
    const top = height * 0.18;
    const y = horizon - (horizon - top) * sunHeight(progress);
    const radius = width * 0.14;

    // céu: a paleta vai da mais escura (em cima) à mais clara (no horizonte); abaixo do horizonte, a mais escura
    const sky = ctx.createLinearGradient(0, 0, 0, horizon);
    palette.forEach((color, i) => sky.addColorStop(i / Math.max(palette.length - 1, 1), color));
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, width, horizon);
    ctx.fillStyle = palette[0];
    ctx.fillRect(0, horizon, width, height - horizon);

    // halo: cresce com a batida e com o refrão
    const halo = radius * (2.5 + 6 * pulse + 0.5 * intensity);
    const glow = ctx.createRadialGradient(width / 2, y, 0, width / 2, y, halo);
    glow.addColorStop(0, "rgba(255, 220, 140, 0.9)");
    glow.addColorStop(1, "rgba(255, 220, 140, 0)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, width, height);

    // disco do sol
    ctx.fillStyle = "#FFF4D6";
    ctx.beginPath();
    ctx.arc(width / 2, y, radius, 0, Math.PI * 2);
    ctx.fill();

    // faixa de névoa no horizonte, por cima da parte de baixo do sol
    const band = ctx.createLinearGradient(0, horizon - 120, 0, horizon + 120);
    band.addColorStop(0, "rgba(255, 200, 120, 0)");
    band.addColorStop(0.5, "rgba(255, 200, 120, 0.35)");
    band.addColorStop(1, "rgba(255, 200, 120, 0)");
    ctx.fillStyle = band;
    ctx.fillRect(0, horizon - 120, width, 240);
  }, [width, height, palette, intensity, pulse, progress]);

  return (
    <AbsoluteFill>
      <canvas ref={canvas} width={width} height={height} style={{ width: "100%", height: "100%" }} />
    </AbsoluteFill>
  );
};
