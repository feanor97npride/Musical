# Testes e validação

## Duas camadas
1. **Automática (`pytest`):** parser da letra, validação do JSON, pós-processamento dos tempos, cache da pipeline, recusas da web, validação do tema. Não carrega modelos nem chama a API.
2. **Manual:** só uma pessoa ouvindo e assistindo consegue dizer se a legenda está no tempo. O Claude Code não escuta o áudio.

## Matriz de músicas de teste
Escolha 5 músicas suas, com letra completa, e salve em `samples/` (áudio não vai para o Git).

| # | Perfil | O que testa |
|---|--------|-------------|
| 1 | Balada lenta, voz clara | Caso fácil; define a linha de base |
| 2 | Música rápida ou rap | Palavras curtas e coladas |
| 3 | Refrão repetido várias vezes | Alinhador se perdendo em repetições |
| 4 | Longa introdução ou solo instrumental | Legenda deve sumir nos trechos sem voz |
| 5 | Backing vocals e ad-libs fora da letra | Ruído extra que o alinhador não espera |

Registre os resultados na tabela de baixo.

## Como conferir a sincronia (10 minutos por música)
1. Rode `python -m engine.align ...` e guarde a tabela de tempos impressa.
2. Sorteie 10 versos, espalhados pela música (início, meio, fim, refrão).
3. Para cada um, abra o MP3 em um player e vá ao tempo `start` impresso.
4. Anote o desvio: o verso começa ouvido antes ou depois do tempo? Quanto, aproximadamente?
5. Gere o vídeo de 30 s ao redor do trecho mais problemático e assista com som.

## Critérios
- **Bom:** desvio de até 0,3 s em pelo menos 9 dos 10 versos.
- **Aceitável:** desvio constante (todos adiantados ou atrasados). Resolve com `--offset`.
- **Falha:** desvio crescente ao longo da música ou versos inteiros no lugar errado. Investigar: letra diferente do que foi cantado, refrão abreviado, vocais não separados, modelo pequeno demais (tente `--model medium`).

## Checklist de cada vídeo
- [ ] Áudio presente e sem corte no início ou no fim
- [ ] Legenda dentro da área segura (nada colado nas bordas)
- [ ] Texto legível em todos os pontos do fundo
- [ ] Sem legenda nos trechos instrumentais longos
- [ ] Refrão visivelmente mais intenso que a estrofe
- [ ] Paleta e fonte coerentes com o tema da música
- [ ] Os três estilos funcionam (`highlight`, `oneword`, `karaoke`)
- [ ] Trocar só o estilo não reprocessou Demucs nem alinhamento

## Resultados
| # | Música | Modelo | Separou vocais? | Bom/Aceitável/Falha | Observações | Tempo total |
|---|--------|--------|-----------------|---------------------|-------------|-------------|
| 1 | O Deserto Vai Florir | small | Sim (Demucs) | Bom (relatado pelo autor) | 56 versos, sem sobreposição; 3 pontos conferidos de ouvido (5,84 s, 98,26 s, 219,72 s) | não medido |
| 2 |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |
| 4 |  |  |  |  |  |  |
| 5 |  |  |  |  |  |  |

## Medidas de desempenho (F5)
- Máquina: 4 vCPU, 15 GB de RAM, sem GPU.
- Música de ~4 min (242 s, "O Deserto Vai Florir"), pipeline completa do zero: ~12 min (separar 124 s + alinhar 55 s + tema 4 s + render 539 s).
- Demucs sozinho: 124 s.
- Alinhamento sozinho: 55 s.
- Render de 30 s (trecho 0–30 s de "O Deserto Vai Florir", estilo oneword, fundo gradiente; 900 quadros, 13,4 MB):
  padrão do Remotion (2 processos neste PC), 71,1 s e 65,5 s (média 68 s); com `--concurrency 4`, 58,9 s e 59,2 s (média 59 s).
  Ganho de ~13%, abaixo do limite de 20%: o padrão não mudou. A opção existe como `RENDER_CONCURRENCY` em `renderer/scripts/render.mjs`, vazia por padrão.
  Memória do sistema (campo "usado" do `free`, amostrado a cada 2 s): pico de ~2,0 GB no padrão e ~2,2 GB com 4 processos.
- Render da música inteira: 539 s (7277 quadros).
- Trocar só o `--style` (cache): 520 s. Pulou Demucs, alinhamento e tema; o render continua sendo quase todo o tempo.

## Fundos (Fase 3: aurora)
- Render de 10 s (trecho 0–10 s de "O Deserto Vai Florir", estilo oneword, 300 quadros), 3 repetições de cada, na mesma máquina de 4 vCPU:
  - degradê: 24,9 s, 23,9 s e 25,2 s (média 24,7 s);
  - aurora: 27,1 s, 26,7 s e 26,4 s (média 26,7 s).
  - Diferença de +8%, abaixo do limite de 20% proposto no plano.
- Determinismo: as 3 repetições da aurora deram quadros de vídeo idênticos (`framemd5`).
- Visual: legenda branca legível sobre a aurora (quadro em 22,5 s de um trecho de 14–24 s).

## Animações (Plano 5)
- Batidas (Fase 1): na música de teste, 555 batidas (bpm 143,55, duração 242,6 s). A primeira em 0,163 s e a última em 237,331 s. Esperado ~580 pelo bpm: o método acha cerca de 4% menos batidas.
- Legendas (Fase 2): render de 10 s do trecho 14–24 s, estilo highlight. Três quadros conferidos a olho: entrada, meio e saída de um verso. Sem medição de tempo separada.
- Fundo (Fase 3), 10 s, estilo oneword, gradiente, 3 repetições cada, na máquina de 4 vCPU:
  - antes da fase (referência): 26,2 s, 25,5 s e 25,0 s (média 25,6 s);
  - versão entregue (commit `a2fe106`): 30,7 s, 31,3 s e 32,1 s (média 31,4 s), **+23%**. Acima do limite de +20%; o usuário decidiu manter.
  - Quadros iguais nas 3 repetições (`framemd5`).
  - Isolamento: gradiente antigo com partículas novas: 26,2 s de média (+2%). Gradiente novo com partículas antigas: 30,3 s (+19%). O custo está no gradiente.
  - Tentativa descartada: gradiente em um só elemento, com cores transparentes no lugar de camadas com opacidade: 33,5 s de média (+31%). Mais lenta, por isso não foi para o repositório.
- Render da música inteira com a Fase 3: não medido. Estimativa: 539 s × 1,23 ≈ 11 minutos na máquina de 4 vCPU.
