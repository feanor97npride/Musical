# Lyric Video Generator

Gera um vídeo vertical com legendas palavra por palavra (estilo TikTok) e fundo animado coerente com o tema, a partir de um MP3 e da letra da música.

> Status: MVP em construção. Veja a fase atual em `CLAUDE.md`.

## Pré-requisitos
- Python 3.10 ou superior
- Node.js 18 ou superior
- FFmpeg
- Git
- Chave da API da Anthropic (opcional; sem ela o tema usa uma paleta padrão)

## Como começar com o Claude Code
1. Crie uma pasta para o projeto e copie estes arquivos para ela, mantendo a estrutura (`CLAUDE.md`, `README.md`, `docs/`).
2. Abra o Claude Code dentro da pasta e selecione o Haiku com `/model`.
3. Abra `docs/PROMPTS.md` e cole o prompt da **F0**. Depois siga a ordem: F1a, F1b, F2, F3, F4, F5, F6.
4. Antes de cada fase seguinte, confira o critério de aceite e faça o teste manual descrito em `docs/TESTES.md`.

## Documentação
| Arquivo | Conteúdo |
|---------|----------|
| `CLAUDE.md` | Regras e contexto lidos pelo Claude Code a cada sessão |
| `docs/ESCOPO.md` | O que entra e o que não entra no MVP, fases e critérios |
| `docs/ARQUITETURA.md` | Pastas, formato dos JSONs, CLI e regras do renderer |
| `docs/PROMPTS.md` | Prompts prontos, um por fase |
| `docs/TESTES.md` | Músicas de teste, critérios de sincronia e checklist |

## Uso (quando o MVP estiver pronto)
```
python -m engine.pipeline --audio samples/minha.mp3 --lyrics samples/minha.txt --style karaoke --clip 30:75
```
O vídeo sai em `output/<slug>/video-<variante>.mp4`: sem `--clip` é `video-karaoke-gradient.mp4`; com `--clip 30:75` é `video-karaoke-gradient-30-75.mp4`.

## Direitos autorais
Use apenas músicas próprias ou com autorização do titular.
