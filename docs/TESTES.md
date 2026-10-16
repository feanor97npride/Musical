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

## Medidas de desempenho (preencher na F5)
- Máquina (CPU/GPU, RAM):
- Música de ~3 min, pipeline completa:
- Demucs sozinho:
- Alinhamento sozinho:
- Render de 30 s:
- Render da música inteira:
