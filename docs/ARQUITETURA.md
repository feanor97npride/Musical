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
│   ├── pipeline.py    # CLI de ponta a ponta
│   ├── render.py      # render dos cortes numa só execução do renderer
│   ├── batch.py       # lote: cada par MP3 + letra de uma pasta
│   ├── cuts.py        # divide a música em cortes
│   ├── export.py      # cópia pronta para postar (ffmpeg)
│   ├── names.py       # nomes de pastas e arquivos
│   ├── checks.py      # regras do song.json
│   ├── postprocess.py # ajustes dos tempos do alinhador
│   ├── steps.py       # etapas da pipeline e progresso
│   ├── write_lyrics.py # letra a partir de um contexto (Claude API)
│   └── posting.py     # textos para postar (YouTube, TikTok, hashtags)
├── renderer/          # projeto Remotion
│   ├── public/audio/  # MP3 copiado pelo pipeline (não versionar)
│   └── src/
│       ├── index.ts
│       ├── Root.tsx
│       ├── LyricVideo.tsx
│       ├── types.ts
│       ├── motion.ts, sun.ts, text.ts, timing.ts, fonts.ts
│       ├── backgrounds/   # Background, Gradient, Particles, Aurora, AuroraGL, Sunrise
│       └── subtitles/     # Highlight, OneWord, Karaoke, Motion, SafeArea
├── web/
│   ├── app.py         # FastAPI
│   ├── jobs.py        # fila de jobs (um por vez)
│   ├── pacote.py      # pacote para postar (ZIP com as cópias e o postar.txt)
│   ├── launcher/      # iniciador do Windows (python -m web.launcher)
│   └── static/        # index.html, style.css, app.js, entrega.js, forms.js, lyrics.js, _headers, termos.html, privacidade.html
├── tests/
├── samples/           # áudio e letras de teste (áudio fora do Git)
└── output/<slug>/     # artefatos de cada job
```

`<slug>` = nome do arquivo de áudio sem extensão + `-` + 8 primeiros caracteres do SHA-1 de (bytes do áudio + texto da letra). Mudou áudio ou letra, muda o slug.

Artefatos em `output/<slug>/`: `vocals.wav`, `song.json`, `props-<variante>.json`, `video-<variante>.mp4`.
`<variante>` = `<estilo>-<fundo>`, com `-16x9` no formato horizontal e `-<início>-<fim>` quando há trecho (ex.: `karaoke-gradient`, `karaoke-gradient-16x9`, `karaoke-solid-0-30`). Cada variante tem o seu vídeo: trocar estilo, fundo ou trecho não apaga os outros.

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
  "audio": { "file": "musica.mp3", "duration": 187.4, "bpm": 96.0, "beats": [0.41, 1.03, 1.65] },
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
- `audio.beats` é opcional: lista de tempos das batidas, em segundos, em ordem crescente e dentro da duração. O passo "Achando batidas" do pipeline grava esse campo.
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
  "clip": { "start": 30.0, "end": 75.0 },
  "backgroundFile": "bg/musica-ab12cd34.jpg"
}
```
- `audioFile` é relativo a `renderer/public/`.
- `backgroundFile` só existe com `style.background` = `image`: é a imagem enviada pelo usuário, cortada no centro (9:16, ou 16:9 com `format` horizontal) e copiada para `renderer/public/bg/` (relativo a `renderer/public/`).
- `format` (opcional) = `"horizontal"` para 16:9 (1920x1080), para o YouTube. Ausente = vertical 9:16 (1080x1920), como antes; por isso os `props.json` verticais não mudam.
- `style.subtitle` ∈ {`highlight`, `oneword`, `karaoke`}; `style.background` ∈ {`solid`, `gradient`, `aurora`, `aurora-gl`, `sunrise`, `image`}. `image` usa a imagem enviada pelo usuário, cortada no centro para 1080x1920 em `output/<slug>/background.jpg` (refeita só quando a imagem muda); zoom e deslocamento suave, com sobreposição escura para a legenda. `aurora-gl` é a mesma aurora desenhada por um shader WebGL (three.js): visual igual, custo de render maior (ver `docs/TESTES.md`).
- `clip` pode ser `null` (música inteira). Com `clip`, o vídeo começa em `clip.start` e o tempo das legendas é deslocado de acordo.

## Regras do renderer
- Composição `LyricVideo`, 1080x1920, 25 fps (constante `FPS` em `renderer/src/Root.tsx`). Duração calculada a partir do `clip` ou de `audio.duration` (use `calculateMetadata`).
- Linha ativa: a que contém o instante atual. Se não houver linha ativa por mais de 0,5 s, não mostrar legenda.
- Palavra atual: a que contém o instante atual dentro da linha ativa.
- Área segura: margem de 12% no topo e 22% embaixo; legendas ficam dentro dela.
- Legenda: o verso entra subindo e aumentando em 0,25 s e sai desvanecendo nos últimos 0,25 s. A palavra atual cresce até 5% em 0,18 s (`Highlight` e `OneWord`).
- `section == "chorus"` aumenta a intensidade visual, sem salto (entra e sai em 0,6 s): o brilho do fundo sobe 12%, o halo cresce, as partículas ficam maiores e mais visíveis, e a legenda fica 3% maior. A velocidade não muda, para não dar salto.
- Pulso na batida: usa `audio.beats` (batidas reais) quando existe, com pico de 3% de brilho que decai em menos de 0,3 s. Sem `audio.beats`, usa a grade do `audio.bpm` contada desde o tempo zero.

## CLI
- `python -m engine.align --audio A --lyrics L --out O [--model small] [--no-separate] [--language pt]`
- `python -m engine.theme --song O` (grava `theme` no mesmo JSON)
- `python -m engine.write_lyrics --context "texto" | --context-file C --out samples/nome.txt [--force]` (gera a letra com `[Verse]`/`[Chorus]`; grava o prompt de estilo do Suno em `samples/nome.estilo.txt` e as informações para postar em `samples/nome.postar.txt`)
- `python -m engine.pipeline --audio A --lyrics L [--style karaoke] [--background gradient] [--clip 30:75] [--no-separate] [--skip-theme] [--background-image ARQUIVO.jpg] [--format vertical|horizontal] [--force]` (com `--background image`, o arquivo é obrigatório; `--format horizontal` gera 16:9)
- `cd renderer && npm run render -- <props.json> <saida.mp4>`
- `cd renderer && npm run render-batch -- <manifesto.json>` (uso interno da pipeline: todos os cortes de uma música numa execução, com um bundle; cada render abre o seu navegador, como o CLI; o manifesto é uma lista de `{props, video, finalProps, finalVideo}`)

## Variáveis de ambiente (`.env`)
- `THEME_API_KEY` — chave da Claude API para o tema (opcional; aceita `ANTHROPIC_API_KEY` como reserva; sem nenhuma usa tema padrão)
- `THEME_MODEL` — modelo para a análise de tema (padrão `claude-haiku-5-5`)
- `LYRICS_MODEL` — modelo que escreve a letra a partir do contexto (padrão `claude-sonnet-5-5`; usa a mesma `THEME_API_KEY`)
- `WHISPER_MODEL` — modelo do alinhador (padrão `small`)
- `ACCESS_TOKEN` — senha da web; a página envia no cabeçalho `X-Access-Token`. Vazio = sem senha (uso local)
- `ALLOWED_ORIGINS` — sites que podem chamar a API de outro endereço (CORS), separados por vírgula. Vazio = só a própria web
- `SITE_URL` — endereço fixo do site no Cloudflare Pages, usado pelo iniciador para abrir o site (sem barra no final)
- `PORT` — porta do servidor local usada pelo iniciador (padrão `8000`)
- `CLOUDFLARED_BIN` — caminho do `cloudflared` quando ele não está no PATH (opcional)
- `RENDER_CONCURRENCY` — número de processos do render (opcional; vazio = padrão do Remotion). Lido por `renderer/scripts/render.mjs` e `render-batch.mjs`
- `BROWSER_EXECUTABLE` — caminho de um Chrome ou headless shell já instalado, para o render (opcional). Lido por `renderer/scripts/render.mjs` e `render-batch.mjs`
- `TUNNEL_TOKEN` — token do túnel fixo da Cloudflare. É uma senha: nunca versionar. Vazio = túnel aleatório
- `TUNNEL_HOSTNAME` — endereço fixo do túnel, ex.: `meu-servidor.seudominio.com`. Obrigatório junto com `TUNNEL_TOKEN`

## Publicação em duas partes (opção B1)
- A página `web/static/` vai para o Cloudflare Pages (projeto Pages com build output directory `web/static`, sem build command).
- Contra cache antigo: `web/static/_headers` manda o navegador revalidar (`Cache-Control: no-cache`), e o `index.html` chama `style.css?v=N`, `app.js?v=N`, `entrega.js?v=N`, `forms.js?v=N` e `lyrics.js?v=N`. Ao mudar um desses arquivos, suba o número `N` no `index.html`.
- A API roda no seu computador (`uvicorn web.app:app --port 8000`) e fica acessível por um túnel (ex.: Cloudflare Tunnel).
- No seu computador, o `.env` precisa de `ACCESS_TOKEN` (uma senha longa) e `ALLOWED_ORIGINS=https://SEU-SITE` (o endereço do site, sem barra no fim).
- Na página, o campo "Endereço do servidor" recebe a URL do túnel, e o campo "Senha de acesso" recebe a senha.
- `POST /lyrics` (campo `context`, até 4000 caracteres, com a mesma senha) devolve `{title, lyrics, style, youtube_title, youtube_description, tiktok_caption, hashtags}` (hashtags é uma lista de 3 a 6). Contexto vazio ou longo dá 400; sem chave da API ou resposta inválida dá 503. A página preenche a letra, o estilo do Suno, o título e a descrição do YouTube, a legenda do TikTok e as hashtags.
- `GET /jobs/{id}` devolve, além de `status`, `stage` e `message`, os campos `step` e `total` (etapa atual e número de etapas, lidos da linha `[n/total] Nome...` da pipeline; `0` até a primeira etapa) e `progress` (de 0 a 1, nunca diminui; durante o render conta os quadros `Rendered a/b`; vale 1 quando termina). A página usa `progress` na barra e `step`/`total` no texto "Etapa X de Y".
- `POST /jobs/{id}/variante` (campos `format` e `cuts`, mesmas regras de `POST /jobs`) cria outro job com o MP3, a letra e os textos do job `{id}`: é o segundo formato do preset "full". A pipeline reaproveita o `song.json` do cache, então só o render roda de novo.
- Presets da página (`web/static/presets.js`, só no navegador): "Full" = 16:9 inteiro + 9:16 em cortes de 90 s; "TikTok" = 9:16 em cortes de 90 s; "YouTube" = 16:9 inteiro; todos com estilo karaokê. Escolher um preset preenche os campos; mudar um campo na mão volta para "Personalizado".
- Biblioteca (`web/biblioteca.py`, `web/library.py`, `web/delivery.py`): as músicas vêm de uma pasta sincronizada no PC pelo Google Drive para computador (`DRIVE_INPUT_DIR`), com uma subpasta por música contendo exatamente um MP3 e um TXT, e uma imagem opcional (`fundo.jpg`/`.png`). `GET /biblioteca` lista as músicas válidas; `POST /biblioteca/{nome}/jobs` gera uma delas com as mesmas opções de `POST /jobs` (a confirmação continua obrigatória). Quando termina, o job copia os MP4 prontos e o `postar.txt` para `DRIVE_OUTPUT_DIR/<nome>/` (só músicas da biblioteca; uma falha de cópia não derruba o job). Sem `DRIVE_INPUT_DIR`, a rota responde 404; pasta inexistente, 409.
- Letra pelo áudio (`engine/transcribe.py`, `web/letra.py`): `python -m engine.transcribe --audio <mp3> --out <txt>` separa a voz (pasta `<nome>-voz/` ao lado do texto), transcreve com Whisper (`WHISPER_MODEL`) e agrupa as palavras em versos (pausa de 1 s ou 8 palavras). O texto sai sem marcadores de seção. No site, `POST /letra` (MP3) cria um job de tipo `letra` (`kind` no status) e `GET /jobs/{id}/letra` devolve o texto; a página põe o texto no campo de letra para revisão antes de gerar o vídeo.
- `GET /historico` (lista: id, data, título), `GET /historico/{id}` (letra completa) e `DELETE /historico/{id}` (204) ficam com a senha. Cada `POST /lyrics` com sucesso grava a letra em `output/historico/letras.json` (fora do Git); arquivo corrompido vai para `letras.corrompido.json`.
- Todo job roda a pipeline com `--export`: cada vídeo ganha a cópia para postar em `output/<slug>/para-postar/` (H.264 yuv420p, moov no começo). O render já sai em yuv420p com cores bt709 (`render-batch.mjs`), então a cópia só remuxa com `-c copy`; vídeo que não está nesse formato (ex.: `yuvj420p` de renders antigos) é recodificado.
- `POST /jobs` aceita o campo opcional `draft` (JSON com `youtube_title`, `youtube_description`, `tiktok_caption` e `hashtags`, os textos que a letra gerou). A página só envia quando os quatro estão completos. Textos fora das regras de postagem dão 400; sem `draft`, o pacote traz só os nomes e os capítulos.
- `GET /jobs/{id}/pacote.zip` devolve o pacote de um job pronto, sem compactar (os MP4 já são comprimidos): as cópias com nomes legíveis (`01-musica-parte-1-de-N.mp4`, ou `musica.mp4` no vídeo único) e um `postar.txt` (UTF-8 com BOM). O `postar.txt` tem um bloco por arquivo (com "Parte X/N · " no título e na legenda, legenda cortada em 150 caracteres) e, no fim, a descrição do YouTube com os capítulos de `song.json` (um por troca de seção, `00:00` no início). O ZIP fica na pasta do job (`pacote.zip`) e é reaproveitado; sem job pronto dá 409.

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
