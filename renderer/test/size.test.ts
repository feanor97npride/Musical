// Self-check do tamanho do vídeo: 16:9 para o horizontal, 9:16 para o vertical e para quando o formato não vem. Rode com npm test.
import { sizeFor } from "../src/size.ts";

const check = (ok: boolean, message: string) => {
  if (!ok) throw new Error(message);
};

check(sizeFor("horizontal").width === 1920 && sizeFor("horizontal").height === 1080, "horizontal deve ser 1920x1080");
check(sizeFor("vertical").width === 1080 && sizeFor("vertical").height === 1920, "vertical deve ser 1080x1920");
check(sizeFor(undefined).height === 1920, "sem formato deve ser vertical (props antigos)");
