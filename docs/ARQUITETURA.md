# Arquitetura

## Fluxo

```
MP3 + letra
   │
   ├─ lyrics.py    interpreta a letra (versos, seções)
   ├─ separate.py  Demucs → vocals.wav (opcional)
   ├─ align.py     stable-ts → tempo por palavra → song.json
   ├─ theme.py     Claude API → theme dentro do song.json
   ├─ props.py     monta props.json (song + estilo + trecho)
   └─ renderer/    Remotion → video.mp4
```

Cada etapa lê e escreve arquivos em `output/<slug>/`. Se o arquivo de saída da etapa já existe, a etapa é pulada (cache), a não ser que se passe `--force`.

## Estrutura de pastas

```
.
├── CLAUDE.md
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── docs/
│   ├── ESCOPO.md
│   ├── ARQUITETURA.md
│   ├── PROMPTS.md
│   └── TESTES.md
├── engine/
│   ├── __init__.py
│   ├── schema.py      # dataclasses e validate_song()
│   ├── lyrics.py      # parse da letra
│   ├── separate.py    # Demucs
│   ├── audio.py       # duração e BPM (librosa)
│   ├── align.py       # alinhamento forçado + CLI
│   ├── theme.py       # análise de tema (Claude API)
│   ├── props.py       # build_props()
│   └── pipeline.py    # CLI de ponta a ponta
├── renderer/          # projeto Remotion
│   ├── public/audio/  # MP3 copiado pelo pipeline (não versionar)
│   └── src/
│       ├── index.ts
│       ├── Root.tsx
│       ├── LyricVideo.tsx
│       ├── types.ts
│       ├── backgrounds/   # Gradient, Particles
│       └── subtitles/     # Highlight, OneWord, Karaoke
├── web/
│   ├── app.py         # FastAPI
│   └── static/index.html
├── tests/
├── samples/           # áudio e letras de teste (áudio fora do Git)
└── output/<slug>/     # artefatos de cada job
```

`<slug>` = nome do arquivo de áudio sem extensão + `-` + 8 primeiros caracteres do SHA-1 de (bytes do áudio + texto da letra). Mudou áudio ou letra, muda o slug.

Artefatos em `output/<slug>/`: `vocals.wav`, `song.json`, `props.json`, `video.mp4`.

## Formato da letra

Arquivo `.txt` em UTF-8.
- Uma linha de texto = um verso (uma "linha" de legenda).
- Linha em branco separa blocos e é ignorada no alinhamento.
- Marcadores de seção ficam entre colchetes em linha própria, por exemplo `[Verso]`, `[Refrão]`, `[Ponte]`, `[Intro]`, `[Outro]`. Também aceita `[Verse]`, `[Chorus]`, `[Bridge]`.
- Marcadores nunca entram no texto alinhado.
- Sem marcador, a seção é `verse`.
- Escreva a letra completa, sem abreviações como "(2x)", porque o alinhador se perde em repetições abreviadas.

Mapeamento de seções: Verso/Verse → `verse`, Refrão/Chorus/Final Chorus → `chorus`, Ponte/Bridge → `bridge`, Intro → `intro`, Outro → `outro`, Pre-Chorus → `verse`, qualquer outro → `other`. Número no fim do marcador é ignorado (`[Verse 1]` vale como `[Verse]`).

## Contrato: `song.json` (versão 1)

```json
{
  "version": 1,
  "language": "pt",
  "audio": { "file": "musica.mp3", "duration": 187.4, "bpm": 96.0 },
  "lines": [
    {
      "id": 0,
      "text": "Texto do verso",
      "section": "verse",
      "start": 12.30,
      "end": 15.10,
      "words": [
        { "text": "Texto", "start": 12.30, "end": 12.70 },
        { "text": "do",    "start": 12.70, "end": 12.85 },
        { "text": "verso", "start": 12.85, "end": 15.10 }
      ]
    }
  ],
  "theme": null
}
```

Regras que `validate_song()` verifica:
- `version == 1`; `lines` não vazio; ids sequenciais a partir de 0.
- Tempos em segundos (float), com `0 <= start < end <= audio.duration` (tolerância de 0,05 s no fim).
- `audio.bpm` é número maior que zero.
- Dentro de uma linha, palavras em ordem, com `start` não decrescente e `end >= start`.
- `line.start` = início da primeira palavra e `line.end` = fim da última.
- Entre linhas, `start` da próxima ≥ `start` da anterior.
- `section` ∈ {`intro`, `verse`, `chorus`, `bridge`, `outro`, `other`}.
- `theme` é `null` ou um objeto válido (abaixo).

### Objeto `theme`
```json
{
  "title": "Saudade no fim da tarde",
  "mood": "melancólico",
  "keywords": ["saudade", "estrada", "pôr do sol"],
  "palette": ["#1B1B3A", "#693668", "#A74482", "#F84AA7"],
  "font": "Playfair Display",
  "visual_concept": "Gradiente lento em tons de crepúsculo com partículas lentas"
}
```
- `palette`: de 3 a 5 cores hexadecimais (`#RGB`, `#RGBA`, `#RRGGBB` ou `#RRGGBBAA`), da mais escura para a mais clara. A ordem é orientação e não é validada.
- `font`: uma de `Inter`, `Bebas Neue`, `Playfair Display`, `Poppins`, `Montserrat`.
- Se a API falhar ou não houver chave, usar tema padrão definido em `theme.py` (função `default_theme()`).

## Contrato: `props.json` (entrada do Remotion)

```json
{
  "song": { "...": "conteúdo do song.json" },
  "audioFile": "audio/musica-ab12cd34.mp3",
  "style": { "subtitle": "karaoke", "background": "gradient" },
  "clip": { "start": 30.0, "end": 75.0 }
}
```
- `audioFile` é relativo a `renderer/public/`.
- `style.subtitle` ∈ {`highlight`, `oneword`, `karaoke`}; `style.background` ∈ {`solid`, `gradient`}.
- `clip` pode ser `null` (música inteira). Com `clip`, o vídeo começa em `clip.start` e o tempo das legendas é deslocado de acordo.

## Regras do renderer
- Composição `LyricVideo`, 1080x1920, 30 fps. Duração calculada a partir do `clip` ou de `audio.duration` (use `calculateMetadata`).
- Linha ativa: a que contém o instante atual. Se não houver linha ativa por mais de 0,5 s, não mostrar legenda.
- Palavra atual: a que contém o instante atual dentro da linha ativa.
- Área segura: margem de 12% no topo e 22% embaixo; legendas ficam dentro dela.
- `section == "chorus"` aumenta a intensidade visual (brilho, movimento, escala).
- Pulso na batida usando `audio.bpm`, de forma sutil.

## CLI
- `python -m engine.align --audio A --lyrics L --out O [--model small] [--no-separate] [--language pt]`
- `python -m engine.theme --song O` (grava `theme` no mesmo JSON)
- `python -m engine.pipeline --audio A --lyrics L [--style karaoke] [--clip 30:75] [--no-separate] [--skip-theme] [--force]`
- `cd renderer && npm run render -- <props.json> <saida.mp4>`

## Variáveis de ambiente (`.env`)
- `ANTHROPIC_API_KEY` — chave da API (opcional; sem ela usa tema padrão)
- `THEME_MODEL` — modelo para a análise de tema (padrão `claude-haiku-5-5`)
- `WHISPER_MODEL` — modelo do alinhador (padrão `small`)
