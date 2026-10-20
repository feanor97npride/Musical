# Letra a partir de um contexto: write_lyrics() via Claude API e CLI que grava a letra e o prompt de estilo do Suno.
import argparse
import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from engine.lyrics import MARKER, parse_lyrics
from engine.theme import ROOT, parse_reply

MODEL_DEFAULT = "claude-sonnet-5-5"
MAX_CONTEXT = 4000
MAX_STYLE = 200  # shortcut: limite chutado para o campo de estilo do Suno, subir se o campo aceitar mais
MIN_LINES = 4
# shortcut: 6 palavras por linha cabem na tela 1080x1920 com a fonte de 88 px, subir se a legenda ficar apertada
MAX_WORDS = 6
CONNECTORS = {"a", "as", "com", "da", "das", "de", "do", "dos", "e", "em", "mas", "na", "no", "os", "para", "pra",
              "por", "que", "sem", "uma", "um"}
# shortcut: 45 s por tentativa, 2 tentativas, para caber no corte de 100 s do túnel da Cloudflare; subir se a letra chegar cortada
TIMEOUT = 45.0
FIELDS = ("title", "lyrics", "style")
SCHEMA = {
    "type": "object",
    "properties": {field: {"type": "string"} for field in FIELDS},
    "required": list(FIELDS),
    "additionalProperties": False,
}
SYSTEM = (
    "Você escreve letras de música a partir do contexto que a pessoa der. Responda com um JSON com os campos "
    "title, lyrics e style. "
    "lyrics: a letra no idioma do contexto, um verso por linha. Marque as seções com marcadores sozinhos na linha, "
    "usando só estes: [Intro], [Verse], [Pre-Chorus], [Chorus], [Bridge], [Outro]. Tenha ao menos um [Chorus]. "
    "Não escreva indicações de instrumento, de palco ou entre parênteses dentro da letra: tudo nela será cantado. "
    f"style: gênero, clima, instrumentos, tipo de voz e andamento, para o campo de estilo do Suno, em inglês, "
    f"com até {MAX_STYLE} caracteres, sem nomes de artistas ou bandas reais."
)


def write_lyrics(context: str, client: anthropic.Anthropic | None = None) -> dict:
    """Devolve {"title", "lyrics", "style"}. ValueError: contexto inválido. RuntimeError: sem chave ou sem letra."""
    context = context.replace("\r\n", "\n")  # o navegador envia quebras como CRLF; o campo conta cada uma como 1
    if not context.strip():
        raise ValueError("o contexto está vazio")
    if len(context) > MAX_CONTEXT:
        raise ValueError(f"o contexto passa de {MAX_CONTEXT} caracteres")
    if client is None:
        load_dotenv(ROOT / ".env")
        api_key = os.getenv("THEME_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("falta THEME_API_KEY no .env para gerar a letra")
        client = anthropic.Anthropic(api_key=api_key, timeout=TIMEOUT, max_retries=0)  # o laço abaixo já tenta de novo
    reason = "sem resposta"
    for _ in range(2):  # uma tentativa e mais uma
        try:
            data = parse_reply(_ask(client, context))
        except anthropic.AuthenticationError as error:
            raise RuntimeError("a API recusou a chave THEME_API_KEY; confira o .env") from error
        except anthropic.APITimeoutError:
            reason = f"a API demorou mais de {TIMEOUT:.0f} s"
            continue
        except anthropic.APIConnectionError:
            reason = "sem conexão com a API da Anthropic"
            continue
        except anthropic.APIStatusError as error:
            reason = f"a API respondeu com erro {error.status_code}: {error.message}"
            if error.status_code < 500 and error.status_code != 429:  # cota, modelo errado etc.: repetir não ajuda
                raise RuntimeError(f"não consegui gerar a letra ({reason})") from error
            continue
        except ValueError:  # JSON cortado ou inválido
            reason = "a resposta não veio em JSON"
            continue
        problems = _problems(data)
        if not problems:
            draft = {field: data[field].strip() for field in FIELDS}
            draft["lyrics"] = subtitle_lines(draft["lyrics"])
            return draft
        reason = "; ".join(problems)
    raise RuntimeError(f"não consegui gerar a letra ({reason})")


def _ask(client: anthropic.Anthropic, context: str) -> str:
    message = client.messages.create(
        model=os.getenv("LYRICS_MODEL", MODEL_DEFAULT),
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": context}],
        # esforço médio: letra pede pouco raciocínio, e o tempo precisa caber no túnel
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
    )
    if message.stop_reason == "refusal":  # recusa não melhora tentando de novo
        raise RuntimeError("o modelo recusou este contexto; reescreva o pedido")
    # o modelo pode enviar bloco "thinking" antes do texto; junta só os blocos de texto
    return "".join(block.text for block in message.content if block.type == "text")


def subtitle_lines(lyrics: str) -> str:
    """Quebra versos com mais de MAX_WORDS palavras; marcadores ficam, linhas vazias somem."""
    out = []
    for line in lyrics.splitlines():
        if MARKER.fullmatch(line.strip()):
            out.append(line.strip())
        else:
            out.extend(_pieces(line.split()))
    return "\n".join(out)


def _pieces(words: list[str]) -> list[str]:
    if not words:
        return []
    if len(words) <= MAX_WORDS:
        return [" ".join(words)]
    # quebra depois de vírgula; senão, antes de conectivo; cada lado com pelo menos 3 palavras
    spots = [i for i in range(3, len(words) - 2) if words[i - 1].endswith(",")]
    spots = spots or [i for i in range(3, len(words) - 2) if words[i].lower() in CONNECTORS]
    cut = min(spots, key=lambda i: abs(i - len(words) / 2)) if spots else len(words) // 2
    return _pieces(words[:cut]) + _pieces(words[cut:])


def _problems(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["resposta não é um objeto JSON"]
    missing = [field for field in FIELDS if not (isinstance(data.get(field), str) and data[field].strip())]
    if missing:
        return ["campos vazios: " + ", ".join(missing)]
    problems = []
    lines = parse_lyrics(data["lyrics"])
    if len(lines) < MIN_LINES:
        problems.append(f"letra com menos de {MIN_LINES} versos")
    if not any(line["section"] == "chorus" for line in lines):
        problems.append("letra sem [Chorus]")
    if any(line["section"] == "other" for line in lines):
        problems.append("marcador de seção desconhecido")
    if len(data["style"].strip()) > MAX_STYLE:
        problems.append(f"estilo com mais de {MAX_STYLE} caracteres")
    return problems


def style_path(lyrics_path: Path) -> Path:
    """samples/nome.txt -> samples/nome.estilo.txt (o lote não junta esse arquivo com o MP3)."""
    return lyrics_path.with_suffix(".estilo.txt")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera a letra e o prompt de estilo do Suno a partir de um contexto")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--context", help="tema, história, estilo e idioma da música")
    source.add_argument("--context-file", type=Path, help="arquivo .txt com o contexto")
    parser.add_argument("--out", type=Path, required=True, help="arquivo da letra, ex.: samples/nome.txt")
    parser.add_argument("--force", action="store_true", help="sobrescreve a letra se o arquivo já existir")
    args = parser.parse_args(argv)
    if args.out.suffix != ".txt":
        parser.error("--out precisa terminar em .txt")
    if args.out.exists() and not args.force:
        parser.error(f"{args.out} já existe; use --force para sobrescrever")
    try:
        context = args.context if args.context is not None else args.context_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        parser.error(f"não consegui ler {args.context_file}; salve o contexto em UTF-8")
    try:
        draft = write_lyrics(context)
    except (ValueError, RuntimeError) as error:
        print(f"erro: {error}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(draft["lyrics"] + "\n", encoding="utf-8")
    style_path(args.out).write_text(draft["style"] + "\n", encoding="utf-8")
    print(f"título: {draft['title']}")
    print(f"letra: {args.out}")
    print(f"estilo para o Suno ({style_path(args.out)}): {draft['style']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
