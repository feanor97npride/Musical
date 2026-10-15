# Prompts por fase (para o Haiku)

## Como usar
1. Abra o Claude Code na pasta do projeto e selecione o Haiku (comando `/model`).
2. Cole **um prompt por vez**, na ordem. Só passe ao próximo depois de conferir o critério de aceite.
3. Se o seu fluxo usa um modo ou comando próprio (o "ultracode"), coloque-o antes do prompt. Os textos abaixo não dependem dele.
4. Ao terminar cada fase, confira `git log` e a linha "Fase atual" do `CLAUDE.md`.

Todos os prompts seguem o mesmo molde: contexto → tarefa em passos → critério de aceite → o que não fazer → o que reportar.

---

## F0 — Setup

```text
Leia CLAUDE.md, docs/ESCOPO.md e docs/ARQUITETURA.md. Execute SOMENTE a Fase 0.

Tarefa:
1. Mostre as versões de python3 (precisa 3.10+), node (18+), npm, ffmpeg e git. Se algo faltar, PARE e me diga o que instalar. Não tente instalar programas do sistema.
2. Rode git init se ainda não houver repositório. Crie .gitignore cobrindo: .venv/, node_modules/, .env, samples/*.mp3, samples/*.wav, output/, renderer/public/audio/, __pycache__/, .pytest_cache/.
3. Crie as pastas e arquivos de "Estrutura de pastas" de docs/ARQUITETURA.md. Cada arquivo .py ou .ts novo começa só com um comentário de uma linha dizendo para que serve.
4. Crie .venv e requirements.txt com: stable-ts, demucs, librosa, anthropic, fastapi, uvicorn, python-multipart, python-dotenv, pytest. Instale e confirme cada import.
5. Crie .env.example com ANTHROPIC_API_KEY=, THEME_MODEL=claude-haiku-5-5 e WHISPER_MODEL=small.
6. Dentro de renderer/, inicialize um projeto Remotion em branco com TypeScript. Se não tiver certeza do comando atual, consulte a documentação oficial em remotion.dev.

Critério de aceite (mostre a saída real):
- python -c "import stable_whisper, demucs, librosa, anthropic, fastapi" roda sem erro.
- cd renderer && npx remotion --help funciona.

NÃO faça: lógica de negócio, download de modelos, commit de áudio.

Ao final: commit "chore(F0): setup", troque "Fase atual" no CLAUDE.md para F1 e reporte em até 10 linhas.
```

---

## F1a — Schema e parser da letra

```text
Leia CLAUDE.md e docs/ARQUITETURA.md (seções "Formato da letra" e "Contrato: song.json"). Execute SOMENTE esta etapa da Fase 1.

Tarefa:
1. engine/schema.py: dataclasses Word, Line, Audio, Theme, Song e a função validate_song(data: dict) -> list[str] que devolve a lista de erros (vazia se válido), seguindo exatamente as regras de docs/ARQUITETURA.md. Inclua to_dict() e from_dict().
2. engine/lyrics.py: função parse_lyrics(text: str) -> list[dict] com {"text": str, "section": str}. Regras: ignorar linhas em branco, tratar [Marcador] em linha própria como mudança de seção (mapeamento da doc), nunca incluir marcadores no texto, seção padrão "verse". Função auxiliar flat_text(lines) -> str que junta os versos com "\n".
3. tests/test_lyrics.py e tests/test_schema.py com pytest. Cubra: letra sem marcadores, com [Refrão] e [Chorus], linhas em branco duplicadas, acentos, JSON válido, JSON com tempos fora de ordem, JSON com id repetido.

Critério de aceite: pytest passa (mostre a saída).

NÃO faça: chamar Demucs, stable-ts ou qualquer modelo. Nada de CLI ainda.

Ao final: commit "feat(F1): schema e parser da letra" e reporte em até 10 linhas.
```

## F1b — Separação, áudio e alinhamento

```text
Leia CLAUDE.md e docs/ARQUITETURA.md. Execute SOMENTE esta etapa da Fase 1. Já existem engine/schema.py e engine/lyrics.py.

Tarefa:
1. engine/separate.py: separate_vocals(audio: Path, out_dir: Path) -> Path. Chama o Demucs por subprocess (python -m demucs --two-stems=vocals -o <pasta> <audio>), localiza o vocals.wav gerado, copia para out_dir/vocals.wav e devolve o caminho. Se out_dir/vocals.wav já existir, devolve sem rodar de novo (cache). Antes de escrever, rode "python -m demucs --help" e confirme as opções na versão instalada.
2. engine/audio.py: duration(audio: Path) -> float e bpm(audio: Path) -> float com librosa. Atenção: dependendo da versão, o tempo de librosa.beat.beat_track pode vir como array; converta para float.
3. engine/align.py: função align(audio, lyrics_text, language="pt", model_name="small", separate=True, out_dir) -> Song.
   - Carregue o modelo com stable_whisper.load_model(model_name), usando GPU se disponível e CPU se não.
   - Use model.align(...) com o texto de flat_text(). Antes de codar, rode help(model.align) e confirme os parâmetros na versão instalada (existe uma opção para manter a divisão por linhas, algo como original_split). Se não existir, alinhe o texto inteiro e distribua as palavras nos versos contando palavras por verso.
   - Garanta que o número de versos do resultado é igual ao da letra. Se não for, use a distribuição por contagem de palavras.
   - Pós-processamento: tempos monotônicos, line.start e line.end derivados das palavras, nenhum tempo acima da duração do áudio.
   - Preencha audio.duration e audio.bpm; theme = null.
   - Valide com validate_song() antes de salvar. Se houver erros, imprima-os e saia com código 1.
4. CLI em align.py: --audio, --lyrics, --out, --model, --no-separate, --language. Ao final imprima uma tabela com id, início, fim e texto de cada verso (para eu conferir no player).
5. tests/test_align_postprocess.py: teste a parte de pós-processamento com dados falsos, sem carregar modelo.

Critério de aceite (mostre a saída real):
- Rodar com samples/<minha-musica>.mp3 e samples/<minha-musica>.txt gera o JSON, validate_song devolve lista vazia e a tabela aparece.
- pytest passa.

NÃO faça: tema, Remotion, web. Não rode o Demucs duas vezes na mesma música (cache).

Ao final: commit "feat(F1): separação e alinhamento", troque "Fase atual" para F2 e reporte em até 10 linhas, incluindo quanto tempo a música levou para processar.
```

---

## F2 — Composição Remotion básica

```text
Leia CLAUDE.md e docs/ARQUITETURA.md (seções "Contrato: props.json" e "Regras do renderer"). Execute SOMENTE a Fase 2. O projeto Remotion já existe em renderer/.

Tarefa:
1. renderer/src/types.ts: tipos TypeScript equivalentes ao song.json e ao props.json.
2. engine/props.py: build_props(song_path, audio_path, subtitle, background, clip) -> dict. Copia o MP3 para renderer/public/audio/<slug>.mp3 e preenche audioFile. Valide o song antes. Inclua CLI: python -m engine.props --song X --audio Y --style highlight --clip 30:75 --out Z.
3. renderer/src/LyricVideo.tsx e Root.tsx: composição "LyricVideo" 1080x1920, 30 fps. Use calculateMetadata para calcular a duração a partir de clip ou de audio.duration.
   - Toque o áudio com o componente de áudio do Remotion. Para o trecho (clip), confira na documentação da versão instalada como cortar o início e o fim do áudio.
   - Fundo sólido (palette[0] do tema, ou #111111 se não houver tema).
   - Mostre a linha ativa centralizada na área segura e destaque a palavra atual com outra cor.
   - Sem linha ativa por mais de 0,5 s, nenhuma legenda.
   - Com clip, desloque o tempo para que o vídeo comece em clip.start.
4. Script npm "render" que receba <props.json> e <saida.mp4> e script "studio" que abra o Remotion Studio.

Critério de aceite (mostre a saída real):
- Gerar props com um clip de 10 segundos de uma música real e renderizar para output/teste-f2.mp4.
- O arquivo existe, toca com áudio e tem 10 s de duração (confirme com ffprobe).
- Abrir o studio sem erros de TypeScript (npx tsc --noEmit passa).

NÃO faça: gradiente, partículas, outros estilos de legenda, tema. Isso é F3 e F4.

Ao final: commit "feat(F2): composição básica", troque "Fase atual" para F3 e reporte em até 10 linhas. Diga qual comando eu devo rodar para ver o vídeo.
```

---

## F3 — Visual: fundo animado e 3 estilos de legenda

```text
Leia CLAUDE.md e docs/ARQUITETURA.md. Execute SOMENTE a Fase 3. A composição básica da F2 já funciona.

Tarefa:
1. renderer/src/backgrounds/Gradient.tsx: gradiente animado lento usando theme.palette (ou paleta padrão). Deve usar o frame do Remotion para animar. Nada de CSS animation ou setTimeout.
2. renderer/src/backgrounds/Particles.tsx: partículas simples (posições determinísticas a partir de um gerador pseudoaleatório com semente fixa, para o render ser reproduzível).
3. Pulso sutil na batida usando audio.bpm (escala ou brilho com variação de poucos por cento).
4. Intensidade por seção: quando a linha ativa tem section == "chorus", aumente brilho, velocidade e número de partículas.
5. Estilos de legenda em renderer/src/subtitles/:
   - Highlight.tsx: o verso inteiro visível, palavra atual em cor de destaque.
   - OneWord.tsx: uma palavra por vez, grande, no centro da área segura.
   - Karaoke.tsx: verso inteiro com preenchimento de cor progredindo dentro de cada palavra.
   O estilo é escolhido por props.style.subtitle. O fundo, por props.style.background ("solid" ou "gradient").
6. Fonte vinda de theme.font, carregada com @remotion/google-fonts. Se theme for null, use Inter.
7. Todo texto deve ter contraste legível sobre o fundo (sombra ou contorno suave) e ficar dentro da área segura (12% topo, 22% embaixo).

Critério de aceite (mostre a saída real):
- Renderizar 10 s da mesma música com cada um dos 3 estilos, gerando output/f3-highlight.mp4, output/f3-oneword.mp4 e output/f3-karaoke.mp4.
- npx tsc --noEmit passa.
- Me diga o tempo de render de cada um.

NÃO faça: chamada à API, mudança no contrato do JSON, novas dependências além de @remotion/google-fonts (justifique se precisar de outra).

Ao final: commit "feat(F3): fundo animado e estilos de legenda", troque "Fase atual" para F4 e reporte em até 10 linhas.
```

---

## F4 — Tema com a Claude API

```text
Leia CLAUDE.md e docs/ARQUITETURA.md (seção "Objeto theme"). Execute SOMENTE a Fase 4.

Tarefa:
1. engine/theme.py com:
   - default_theme() -> Theme: paleta neutra escura, fonte Inter.
   - analyze_theme(lines_text: str) -> Theme: usa o SDK oficial "anthropic" e o modelo de THEME_MODEL (padrão claude-haiku-5-5). Carregue o .env com python-dotenv.
   - Instrução ao modelo (no system prompt): "Responda APENAS com um JSON, sem texto antes ou depois, sem cercas de código", com os campos title, mood, keywords (3 a 6), palette (3 a 5 cores hex, da mais escura para a mais clara), font (uma de Inter, Bebas Neue, Playfair Display, Poppins, Montserrat) e visual_concept (uma frase).
   - Valide a resposta: remova cercas de código se vierem, faça json.loads, confira os campos, cores no formato #RRGGBB e fonte na lista. Se algo falhar, tente mais 1 vez; depois use default_theme() e imprima um aviso. Nunca derrube a pipeline por causa do tema.
   - Sem ANTHROPIC_API_KEY, use default_theme() sem tentar chamar a API.
2. CLI: python -m engine.theme --song <song.json> grava o campo theme no mesmo arquivo e revalida com validate_song().
3. tests/test_theme.py: teste a validação e o fallback com respostas falsas (mock), sem chamar a API de verdade.
4. Confirme que o renderer usa theme.palette e theme.font (F3 já prevê isso). Ajuste só o necessário.

Critério de aceite (mostre a saída real):
- Duas músicas com temas bem diferentes (por exemplo, uma triste e uma animada) geram paletas diferentes, e os vídeos de 10 s delas têm visuais claramente diferentes.
- Sem chave no .env, o comando termina com tema padrão e sem erro.
- pytest passa.

NÃO faça: escrever a chave da API em qualquer arquivo versionado; mudar o contrato do JSON.

Ao final: commit "feat(F4): tema via API", troque "Fase atual" para F5 e reporte em até 10 linhas.
```

---

## F5 — Pipeline de ponta a ponta

```text
Leia CLAUDE.md e docs/ARQUITETURA.md (seções "Estrutura de pastas", "CLI"). Execute SOMENTE a Fase 5.

Tarefa:
1. engine/pipeline.py com CLI: --audio, --lyrics, --style (padrão karaoke), --clip INICIO:FIM (segundos, opcional), --no-separate, --skip-theme, --force.
2. Calcule o slug (nome do arquivo + 8 primeiros caracteres do SHA-1 do áudio + texto da letra) e use output/<slug>/ para todos os artefatos.
3. Etapas na ordem: separar vocais → alinhar → tema → props → render. Cada etapa é pulada se o artefato já existe, a não ser com --force. Mudar só --style ou --clip deve reaproveitar vocals.wav e song.json e refazer apenas props e render.
4. O render chama "npm run render" no diretório renderer/ via subprocess e mostra a saída.
5. Imprima o progresso por etapa, no formato "[2/5] Alinhando letra... ok (38 s)" e, no fim, o caminho do MP4 e o tempo total.
6. Se uma etapa falhar, imprima qual falhou e a causa, e saia com código diferente de zero sem apagar os artefatos anteriores.
7. tests/test_pipeline_cache.py: teste a lógica de slug e de cache com arquivos falsos, sem rodar modelos.

Critério de aceite (mostre a saída real):
- Um único comando gera output/<slug>/video.mp4 a partir de MP3 + letra.
- Rodar de novo com outro --style termina bem mais rápido e não chama Demucs nem alinhamento.
- pytest passa.

NÃO faça: web, novos estilos, mudanças no renderer além do necessário.

Ao final: commit "feat(F5): pipeline completa", troque "Fase atual" para F6 e reporte em até 10 linhas, incluindo o tempo total de uma música inteira. Anote esse tempo em docs/TESTES.md.
```

---

## F6 — Web mínima

```text
Leia CLAUDE.md e docs/ARQUITETURA.md. Execute SOMENTE a Fase 6.

Tarefa:
1. web/app.py com FastAPI:
   - POST /jobs: recebe multipart com audio (MP3), lyrics (texto), style, clip_start e clip_end opcionais. Valide extensão .mp3, tamanho máximo de 25 MB e letra não vazia. Devolve {"id": ...}.
   - Os jobs rodam em segundo plano, um de cada vez (fila simples em memória). Cada job chama a pipeline da F5 por função ou subprocess.
   - GET /jobs/{id}: devolve {"status": "queued|running|done|error", "stage": "...", "message": "..."}.
   - GET /jobs/{id}/video: devolve o MP4 quando status = done.
2. web/static/index.html: página única, em português, sem framework. Formulário com upload do MP3, caixa de texto da letra, escolha de estilo, campos opcionais de trecho (início e fim em segundos), caixa de confirmação obrigatória "Esta música é minha ou tenho autorização para usá-la". Ao enviar, faz polling do status a cada 2 s, mostra a etapa atual, e quando terminar mostra o vídeo em <video> e um link de download.
3. Sirva a página em "/" com StaticFiles.
4. tests/test_web.py com o TestClient do FastAPI: valide as recusas (arquivo não-MP3, letra vazia, arquivo grande), sem rodar a pipeline de verdade (mock).

Critério de aceite (mostre a saída real):
- uvicorn web.app:app roda; pelo navegador consigo enviar uma música com a letra e baixar o MP4.
- pytest passa.

NÃO faça: login, banco de dados, Next.js, deploy.

Ao final: commit "feat(F6): web mínima", marque "Fase atual: MVP concluído" no CLAUDE.md e reporte em até 10 linhas, com o comando para subir o servidor.
```

---

## Prompts de apoio

### Retomar uma sessão
```text
Leia CLAUDE.md, docs/ESCOPO.md e docs/ARQUITETURA.md. Rode git log --oneline -10 e git status. Diga em até 5 linhas em que fase estamos, o que está pronto e o que falta. Não altere nenhum arquivo.
```

### Corrigir um erro
```text
Ao rodar: <comando>
Apareceu este erro completo:
<cole o erro inteiro>
Leia a mensagem completa, aponte a causa provável em 2 linhas, corrija só o necessário e rode o mesmo comando de novo. Mostre a saída. Não reescreva arquivos inteiros e não mude nada fora do escopo da fase atual.
```

### Legenda fora de sincronia
```text
Na música <nome>, as legendas estão com problema de tempo: <ex.: cerca de 0,4 s atrasadas no refrão / adiantadas em todo o vídeo>.
1. Mostre a tabela de tempos do song.json para os versos <ids> e compare com o que eu observei.
2. Se o desvio for constante, adicione a opção --offset SEGUNDOS ao pipeline e ao props (soma o valor a todos os tempos, sem passar de 0 ou da duração). Documente em docs/ARQUITETURA.md.
3. Se o desvio ocorrer só em alguns trechos, não corrija no código. Me diga quais versos estão errados e hipóteses de causa (refrão repetido, backing vocal, instrumental).
Rode os testes e mostre a saída.
```

### Revisão ao fim de uma fase
```text
Faça uma revisão da fase que acabamos de concluir. Liste em até 10 linhas: o que cumpre o critério de aceite, o que não foi testado, e qualquer arquivo acima de 200 linhas ou função confusa. Não altere nada, só reporte.
```
