// Fonte do tema, carregada com @remotion/google-fonts. Sem tema, usa Inter.
import { loadFont as bebasNeue } from "@remotion/google-fonts/BebasNeue";
import { loadFont as inter } from "@remotion/google-fonts/Inter";
import { loadFont as montserrat } from "@remotion/google-fonts/Montserrat";
import { loadFont as playfair } from "@remotion/google-fonts/PlayfairDisplay";
import { loadFont as poppins } from "@remotion/google-fonts/Poppins";
import type { FontSpec } from "./types";

// Cada fonte pede só o peso que ela tem, e o peso devolvido vai junto para o texto usar.
const LOADERS: Record<string, () => FontSpec> = {
  Inter: () => ({ fontFamily: inter("normal", { weights: ["700"] }).fontFamily, fontWeight: 700 }),
  "Bebas Neue": () => ({ fontFamily: bebasNeue("normal", { weights: ["400"] }).fontFamily, fontWeight: 400 }),
  "Playfair Display": () => ({ fontFamily: playfair("normal", { weights: ["700"] }).fontFamily, fontWeight: 700 }),
  Poppins: () => ({ fontFamily: poppins("normal", { weights: ["700"] }).fontFamily, fontWeight: 700 }),
  Montserrat: () => ({ fontFamily: montserrat("normal", { weights: ["700"] }).fontFamily, fontWeight: 700 }),
};

export const fontFor = (name: string | null | undefined): FontSpec => (LOADERS[name ?? "Inter"] ?? LOADERS.Inter)();
