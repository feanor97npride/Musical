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
   └─ renderer/    Remotion → video-<variante>.mp4
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
│       ├── backgrounds/   # Background, Gradient, Particles, Aurora
│       └── subtitles/     # Highlight, OneWord, Karaoke
├── web/
│   ├── app.py         # FastAPI
│   └── static/           # index.html (formulário) e app.js (script da página)
├── tests/
├── samples/           # áudio e letras de teste (áudio fora do Git)
└── output/<slug>/     # artefatos de cada job
```

`<slug>` = nome do arquivo de áudio sem extensão + `-` + 8 primeiros caracteres do SHA-1 de (bytes do áudio + texto da letra). Mudou áudio ou letra, muda o slug.

Artefatos em `output/<slug>/`: `vocals.wav`, `song.json`, `props-<variante>.json`, `video-<variante>.mp4`.
`<variante>` = `<estilo>-<fundo>`, com `-<início>-<fim>` quando há trecho (ex.: `karaoke-gradient`, `karaoke-solid-0-30`). Cada variante tem o seu vídeo: trocar estilo, fundo ou trecho não apaga os outros.

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
- `style.subtitle` ∈ {`highlight`, `oneword`, `karaoke`}; `style.background` ∈ {`solid`, `gradient`, `aurora`}.
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
- `python -m engine.pipeline --audio A --lyrics L [--style karaoke] [--background gradient] [--clip 30:75] [--no-separate] [--skip-theme] [--force]`
- `cd renderer && npm run render -- <props.json> <saida.mp4>`

## Variáveis de ambiente (`.env`)
- `THEME_API_KEY` — chave da Claude API para o tema (opcional; aceita `ANTHROPIC_API_KEY` como reserva; sem nenhuma usa tema padrão)
- `THEME_MODEL` — modelo para a análise de tema (padrão `claude-haiku-5-5`)
- `WHISPER_MODEL` — modelo do alinhador (padrão `small`)
- `ACCESS_TOKEN` — senha da web; a página envia no cabeçalho `X-Access-Token`. Vazio = sem senha (uso local)
- `ALLOWED_ORIGINS` — sites que podem chamar a API de outro endereço (CORS), separados por vírgula. Vazio = só a própria web
- `SITE_URL` — endereço fixo do site no Cloudflare Pages, usado pelo iniciador para abrir o site (sem barra no final)
- `PORT` — porta do servidor local usada pelo iniciador (padrão `8000`)
- `CLOUDFLARED_BIN` — caminho do `cloudflared` quando ele não está no PATH (opcional)
- `TUNNEL_TOKEN` — token do túnel fixo da Cloudflare. É uma senha: nunca versionar. Vazio = túnel aleatório
- `TUNNEL_HOSTNAME` — endereço fixo do túnel, ex.: `meu-servidor.seudominio.com`. Obrigatório junto com `TUNNEL_TOKEN`

## Publicação em duas partes (opção B1)
- A página `web/static/` vai para o Cloudflare Pages (projeto Pages com build output directory `web/static`, sem build command).
- A API roda no seu computador (`uvicorn web.app:app --port 8000`) e fica acessível por um túnel (ex.: Cloudflare Tunnel).
- No seu computador, o `.env` precisa de `ACCESS_TOKEN` (uma senha longa) e `ALLOWED_ORIGINS=https://SEU-SITE` (o endereço do site, sem barra no fim).
- Na página, o campo "Endereço do servidor" recebe a URL do túnel, e o campo "Senha de acesso" recebe a senha.

## Iniciador (Windows)
- `iniciar.bat` (duplo clique) ou `python -m web.launcher` faz, nesta ordem:
  1. confere o `.env` e a porta; se a porta já estiver em uso, para e avisa;
  2. atualiza o projeto com `git pull --ff-only` e instala `pip` ou `npm ci` só se `requirements.txt` ou `renderer/package-lock.json` mudaram (`--sem-atualizar` pula esta etapa);
  3. liga o servidor (`127.0.0.1:PORT`) e o túnel `cloudflared`;
  4. copia só o endereço do túnel para a área de transferência e abre `SITE_URL/#server=<endereço>` no navegador.
- Sem `ACCESS_TOKEN`, o túnel não é aberto (o servidor fica só local). Sem `cloudflared`, o iniciador segue só local e mostra como instalar.
- Com `TUNNEL_TOKEN` e `TUNNEL_HOSTNAME`, o túnel é o fixo da Cloudflare: roda `cloudflared tunnel run` (o destino fica no painel) e o endereço é `https://TUNNEL_HOSTNAME`, anunciado quando a conexão registra. Sem eles, usa o túnel aleatório (`trycloudflare.com`), cujo endereço muda a cada início.
- Se o servidor ou o túnel cair, o iniciador reinicia o processo; se cair mais de 5 vezes em 1 minuto, desiste e avisa.
- `python -m web.launcher --criar-atalho` cria o atalho na Área de Trabalho (sem binário novo; usa o PowerShell, sem as flags que o antivírus marca).
- Fechar a janela pelo botão X também encerra o servidor e o túnel (no Windows, o iniciador recebe o aviso de fechamento e para tudo antes de sair). `Ctrl + C` continua funcionando.
- Modelo de ameaça do link: a página só aceita no `#server=` o endereço fixo definido em `FIXED_SERVER` (em `web/static/app.js`), e não grava esse endereço no navegador. Mesmo assim, quem recebe um link falso pode induzir a digitação da senha num servidor alheio. Por isso a página mostra o aviso "Se você não abriu pelo iniciador, não digite a senha". Melhoria futura: prova de posse da senha (HMAC com desafio).
