# CLAUDE.md — Lyric Video Generator

## Visão geral
Ferramenta (CLI + web simples) que recebe um MP3 e a letra da música e gera um vídeo vertical (1080x1920, 30 fps) com legendas palavra por palavra no estilo TikTok e fundo animado coerente com o tema da letra.

Pipeline: MP3 + letra → separação de vocais (Demucs) → alinhamento forçado (stable-ts) → `song.json` → tema via Claude API → render (Remotion) → MP4.

## Estado atual
- **Fase atual:** F1 — parser da letra, separação de vocais e alinhamento  <!-- atualize esta linha ao concluir cada fase -->
- Escopo e critérios de aceite: `docs/ESCOPO.md`
- Contratos de dados, pastas e CLI: `docs/ARQUITETURA.md`
- Prompts de cada fase: `docs/PROMPTS.md`
- Validação e músicas de teste: `docs/TESTES.md`

## Stack
- Python 3.10+ com venv em `.venv/`: stable-ts, demucs, librosa, anthropic, fastapi, uvicorn, pytest
- Node 18+ e TypeScript: Remotion, dentro de `renderer/`
- FFmpeg instalado no sistema
- Web do MVP: FastAPI + uma página HTML estática (sem Next.js no MVP)

## Estrutura
- `engine/` — Python: lyrics, separate, align, theme, props, pipeline
- `renderer/` — projeto Remotion (composição `LyricVideo`)
- `web/` — FastAPI e página estática
- `samples/` — músicas e letras de teste (áudio nunca vai para o Git)
- `output/` — artefatos por job, em `output/<slug>/` (nunca vai para o Git)
- `docs/` — documentação do projeto

Detalhes e árvore completa em `docs/ARQUITETURA.md`.

## Comandos
Passam a existir conforme as fases avançam. Quando um comando mudar, atualize esta seção.

- Alinhar: `python -m engine.align --audio samples/a.mp3 --lyrics samples/a.txt --out output/a/song.json`
- Pipeline completa: `python -m engine.pipeline --audio samples/a.mp3 --lyrics samples/a.txt`
- Renderizar: `cd renderer && npm run render -- <props.json> <saida.mp4>`
- Prévia: `cd renderer && npm run studio`
- Web: `uvicorn web.app:app --reload`
- Testes: `pytest`

## Convenções
- Código, nomes de variáveis, funções e chaves de JSON em inglês. Comentários, docs, mensagens de commit e textos de interface em português.
- Python: type hints, funções pequenas, `pathlib` em vez de strings de caminho.
- TypeScript: modo `strict`, componentes pequenos, um componente por arquivo.
- Arquivos com menos de 200 linhas. Se passar disso, divida.
- Commits no formato `tipo(Fx): descrição` (ex.: `feat(F1): alinhamento forçado`).

## Regras (o que NÃO fazer)
- Não avance para a próxima fase sem eu pedir. Uma fase por vez.
- Não mude o contrato do `song.json` ou do props sem atualizar `docs/ARQUITETURA.md` e me avisar.
- Não invente assinatura de biblioteca. Se não tiver certeza, leia a documentação instalada (`help()`, `--help`, pasta `node_modules`) ou a doc oficial.
- Não adicione dependência sem justificar no commit.
- Não exija GPU. Detecte e use CPU como alternativa.
- Não versione áudio, `.env`, `node_modules`, `.venv` nem `output/`.
- Chaves de API só via `.env`. Nunca escreva uma chave em arquivo versionado.
- Não faça refatorações fora do escopo da tarefa.
- Não diga que terminou sem rodar o comando de aceite da fase.
- Se uma decisão for ambígua, pare e pergunte em vez de assumir.

## Fluxo de trabalho por tarefa
1. Leia este arquivo e os docs citados no prompt.
2. Escreva um plano de 3 a 5 linhas antes de mexer em código.
3. Implemente só o que a tarefa pede.
4. Rode o critério de aceite e os testes.
5. Faça commit e atualize "Fase atual" acima.
6. Responda em no máximo 10 linhas: o que foi feito, como testar, o que falta.

## Notas para modelos pequenos (Haiku)
- Trabalhe em passos curtos e confirme cada comando antes do próximo.
- Mostre a saída real dos comandos de aceite. Não resuma de memória.
- Em erro, leia a mensagem completa, corrija a causa e rode de novo. Não reescreva arquivos inteiros por palpite.
- Prefira a solução mais simples que cumpra o critério de aceite.

## Aviso legal
A interface web deve exibir um aviso: enviar apenas músicas próprias ou com autorização.
