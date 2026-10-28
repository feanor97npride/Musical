# CLAUDE.md — Lyric Video Generator

## Visão geral
Ferramenta (CLI + web simples) que recebe um MP3 e a letra da música e gera um vídeo vertical (1080x1920, 25 fps) com legendas palavra por palavra no estilo TikTok e fundo animado coerente com o tema da letra.

Pipeline: MP3 + letra → separação de vocais (Demucs) → alinhamento forçado (stable-ts) → `song.json` → tema via Claude API → render (Remotion) → MP4.

## Estado atual
- **Fase atual:** MVP concluído (F6: web mínima com FastAPI). Plano 6 (automações): Fases A, B e C concluídas; Fase D (postagem pela API) pausada. Planos 8 e 10 a 23 (letra por IA, visual, layout, progresso, cache, segurança, formato 16:9, imagem enviada, cortes em ZIP, histórico de letras e pacote para postar) concluídos e publicados. Depois: biblioteca do Google Drive (entrada e saída), letra pelo áudio, fila e site endurecidos, motor com cache de voz por áudio, render em 25 fps, redesign V3 do site, Drive automático (inclusive sem TXT) e aviso no Telegram  <!-- atualize esta linha ao concluir cada fase -->
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
- `web/` — FastAPI, página estática e iniciador (`web/launcher/`, arquivo de duplo clique `iniciar.bat`)
- `samples/` — músicas e letras de teste (áudio nunca vai para o Git)
- `output/` — artefatos por job, em `output/<slug>/` (nunca vai para o Git)
- `docs/` — documentação do projeto

Detalhes e árvore completa em `docs/ARQUITETURA.md`.

## Comandos
Passam a existir conforme as fases avançam. Quando um comando mudar, atualize esta seção.

- Gerar letra a partir de um contexto: `python -m engine.write_lyrics --context "tema, história, estilo, idioma" --out samples/nome.txt` (grava também `samples/nome.estilo.txt` para o Suno e `samples/nome.postar.txt` com títulos, descrição, legenda e hashtags)
- Letra pelo áudio (para revisar): `python -m engine.transcribe --audio samples/a.mp3 --out samples/a.txt`
- Alinhar: `python -m engine.align --audio samples/a.mp3 --lyrics samples/a.txt --out output/a/song.json`
- Pipeline completa: `python -m engine.pipeline --audio samples/a.mp3 --lyrics samples/a.txt`
- Lote (cada `.mp3` com `.txt` de mesmo nome na pasta): `python -m engine.batch --folder samples --variants "background=gradient,aurora;style=karaoke,oneword"` (`--variants` é opcional: um vídeo por combinação; `--export` gera também a cópia para postar em `para-postar/`)
- Renderizar: `cd renderer && npm run render -- <props.json> <saida.mp4>`
- Prévia: `cd renderer && npm run studio`
- Web: `uvicorn web.app:app --reload`
- Iniciar tudo (Windows): duplo clique em `iniciar.bat`, ou `python -m web.launcher` (liga servidor e túnel e abre o site)
- Criar atalho na Área de Trabalho (Windows): `python -m web.launcher --criar-atalho`
- Testes: `pytest`

## Convenções
- Código, nomes de variáveis, funções e chaves de JSON em inglês. Comentários, docs e textos de interface em português. Mensagens de commit: ver "Regras de trabalho com o usuário".
- Python: type hints, funções pequenas, `pathlib` em vez de strings de caminho.
- TypeScript: modo `strict`, componentes pequenos, um componente por arquivo.
- Arquivos com menos de 200 linhas. Se passar disso, divida.
- Commits no formato `tipo(Fx): description` (ex.: `feat(F1): add forced alignment`), assunto no imperativo em inglês.

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
5. Mostre o resultado e espere o "ok". Só após o "ok": faça commit, push e atualize "Fase atual" acima.
6. Responda no formato de "Como responder".

## Regras de trabalho com o usuário
- Responda em português.
- Um item por vez: implemente, verifique, mostre o resultado e espere o "ok". Só então faça commit e push.
- Nunca faça commit nem push sem "ok" explícito. O aviso do hook de parada ("há mudanças não commitadas") é automático e não conta como confirmação.
- Push só no branch `claude/nifty-albattani-klepoh` (o branch designado desta sessão e o que o Cloudflare Pages publica). Sem PR, a menos que peçam. Force-push só com autorização explícita, e sempre com `--force-with-lease`.
- Commits: assunto no imperativo em inglês, corpo curto, e trailer só `Claude-Session`. Sem identificador de modelo e sem `Co-Authored-By`.
- Para trazer algo de outro branch, use `git cherry-pick --no-commit`, confira conflitos e só então faça commit.
- Nunca use `| tail` (ou outro pipe) numa condição: o pipe esconde a falha. Guarde o código de saída (`rc=$?`) e siga só se for zero.
- Diga o que não foi testado no ambiente da sessão. Hoje, por exemplo: os modelos do alinhador e do Demucs, se os pesos não puderem ser baixados; e o áudio real, até você enviar uma música em `samples/`.

## Como responder
Explique como se falasse com uma pessoa de 15 anos que nunca programou. Em toda resposta, inclua:
- **O que eu fiz:** em português simples, sem jargão.
- **O que você precisa fazer:** passo a passo, supondo que a pessoa nunca viu aquilo antes.
- **Por quê:** uma frase dizendo o que aquilo faz ou por que importa.
- **Próximo passo:** uma única ação clara.
- **Erros:** se algo deu errado, explique de forma simples e diga exatamente como corrigir.

Quando houver ferramenta externa ou termo que quem não programa não conhece:
- Diga onde achar o que precisa (ex.: "painel do serviço → Configurações → Variáveis").
- Explique em uma frase o que cada chave ou configuração faz.
- Se houver SQL ou comando para rodar, explique o que faz antes de rodar.
- Se for preciso criar à mão uma pasta ou configuração, explique o que é e por que existe.
- Seja conciso. Menos é mais.

## Notas para modelos pequenos (Haiku)
- Trabalhe em passos curtos e confirme cada comando antes do próximo.
- Mostre a saída real dos comandos de aceite. Não resuma de memória.
- Em erro, leia a mensagem completa, corrija a causa e rode de novo. Não reescreva arquivos inteiros por palpite.
- Prefira a solução mais simples que cumpra o critério de aceite.
- Todos os planos devem ser feitos pensados para execução no Haiku: passos curtos, arquivo e linha citados, comando de aceite exato e nenhuma decisão de arquitetura deixada para quem executa.

## Aviso legal
A interface web deve exibir um aviso: enviar apenas músicas próprias ou com autorização.
