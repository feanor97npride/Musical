# Escopo do MVP

## Objetivo
Transformar um MP3 e sua letra em um vídeo vertical com legendas animadas palavra por palavra (estilo TikTok) e fundo animado coerente com o tema da música, de forma automática.

## Uso inicial
Uso pessoal, com músicas próprias e a letra em mãos. Abrir para o público fica para depois do MVP.

## Entradas e saídas
**Entradas**
- Arquivo MP3
- Letra em texto (`.txt` ou campo de texto), com marcadores opcionais de seção como `[Refrão]`
- Ou um contexto (tema, história, estilo, idioma) para a letra ser escrita pela Claude API, com o prompt de estilo para gerar a música no Suno (feito à mão; o Suno não tem API aberta)
- Opções: estilo de legenda (`highlight`, `oneword`, `karaoke`) e trecho (início e fim em segundos)

**Saídas**
- `song.json` com o tempo de cada palavra (contrato em `ARQUITETURA.md`)
- Vídeo MP4 1080x1920, 30 fps, com o áudio da música

## Dentro do MVP
1. Alinhamento forçado letra ↔ áudio com tempo por palavra.
2. Separação de vocais com Demucs (ligada por padrão, com opção de desligar).
3. Vídeo com legendas palavra por palavra em 3 estilos.
4. Fundo procedural animado (gradiente + partículas) usando a paleta do tema.
5. Análise de tema da letra via Claude API (paleta, humor, fonte), com paleta padrão se a API falhar.
6. Seções (estrofe, refrão, ponte) vindas da própria letra, com refrão mais intenso.
7. Escolha de trecho para renderizar só uma parte da música.
8. CLI de ponta a ponta e uma web mínima (upload, progresso, prévia, download).
9. Cache por job para não reprocessar etapas já feitas.

## Fora do MVP
- Transcrição sem letra (Whisper puro)
- Editor visual de legendas
- Imagens ou vídeos de fundo gerados por IA, ou clipes de banco
- Formatos 1:1 e 16:9
- Contas de usuário, pagamento, fila distribuída
- Next.js, deploy em nuvem, GPU dedicada
- Marca d'água, logo e thumbnail automática

## Fases
| Fase | Entrega | Pronto quando |
|------|---------|---------------|
| F0 | Setup do repositório e ambientes | Imports Python e `remotion --help` funcionam |
| F1 | Parser da letra, separação de vocais e alinhamento → `song.json` | JSON válido com tempos crescentes para 1 música real |
| F2 | Composição Remotion lendo o JSON, fundo sólido, legenda destacando a palavra atual | MP4 de 10 s com áudio e legenda no tempo |
| F3 | Fundo animado, 3 estilos de legenda, área segura, intensidade por seção | Os 3 estilos renderizam e ficam legíveis |
| F4 | Tema via Claude API aplicado ao visual | Duas músicas de temas diferentes geram paletas diferentes |
| F5 | Pipeline CLI de ponta a ponta com cache | Um comando gera o MP4 a partir de MP3 + letra |
| F6 | Web mínima com FastAPI | Subir MP3 e letra no navegador e baixar o MP4 |

## Critérios de aceite do MVP
- Em 4 de 5 músicas da matriz de `TESTES.md`, ao menos 90% das linhas amostradas ficam com erro de sincronia de até 0,3 s.
- Legendas sempre dentro da área segura e legíveis sobre o fundo.
- Trechos instrumentais longos (mais de 1 s sem linha ativa) ficam sem legenda.
- Refazer o render com outro estilo não reprocessa Demucs nem o alinhamento.
- Sem chave de API, a pipeline ainda funciona com a paleta padrão.
- `pytest` passa e o render de 10 s funciona em máquina sem GPU.

## Requisitos não funcionais
- Roda em CPU. GPU é opcional.
- Tempo total para uma música de 3 minutos: medir na F5 e registrar em `TESTES.md`. Ainda não há meta fixa.
- Custo por vídeo: a chamada de tema, de poucos centavos. Gerar a letra com IA (opcional) é outra chamada, de alguns centavos.

## Riscos
- **Alinhamento falhar em refrões repetidos, rap rápido ou muito instrumental.** Mitigação: separar vocais, testar com 5 músicas diferentes e manter opção de deslocamento global de tempo.
- **Demucs e Whisper lentos sem GPU.** Mitigação: cache e opção de trecho.
- **Licença do Remotion.** Confira os termos de uso do Remotion para o seu caso (uso pessoal ou comercial) antes de publicar a ferramenta.
- **Direitos autorais da música.** Aviso na interface e uso apenas de material próprio ou autorizado.

## Decisões tomadas
- Alinhamento forçado (stable-ts) em vez de transcrição, porque há letra.
- Remotion para o render, porque legenda palavra por palavra e fundo animado ficam simples em React.
- Fundo procedural no MVP: grátis, rápido e previsível.
- Web com FastAPI e uma página estática, para manter o MVP pequeno. Next.js entra depois.
- Contrato em JSON entre as etapas, para trocar qualquer peça sem refazer o resto.

## Depois do MVP
1. Editor de legendas com ajuste de tempo por verso.
2. Imagens por seção (Flux, SDXL) com movimento suave.
3. Formatos 1:1 e 16:9.
4. Modo sem letra com Whisper.
5. Front em Next.js, contas e limites por usuário.
