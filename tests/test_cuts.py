# Testes dos cortes: versos inteiros, dentro da música, e um render por corte no pipeline (com render falso).
import argparse
import json

import pytest

from engine import pipeline
from engine.cuts import plan_cuts


def song(duration: float, lines: list[tuple[float, float]]) -> dict:
    return {"audio": {"duration": duration}, "lines": [{"start": s, "end": e} for s, e in lines]}


def test_cada_verso_fica_inteiro_em_um_corte_so():
    lines = [(i * 5.0, i * 5.0 + 4.0) for i in range(18)]
    cuts = plan_cuts(song(100.0, lines), 30.0)
    assert len(cuts) == 3
    for start, end in lines:
        assert sum(c0 <= start and end <= c1 for c0, c1 in cuts) == 1


def test_cortes_ficam_perto_do_alvo_e_dentro_da_musica():
    lines = [(i * 5.0, i * 5.0 + 4.0) for i in range(18)]
    for c0, c1 in plan_cuts(song(100.0, lines), 30.0):
        assert 0 <= c0 < c1 <= 100.0
        assert c1 - c0 <= 31.0


def test_ultimo_corte_curto_junta_com_o_anterior():
    lines = [(i * 5.0, i * 5.0 + 4.0) for i in range(13)]  # 6 + 6 + 1 versos: o último é curto demais
    cuts = plan_cuts(song(70.0, lines), 30.0)
    assert len(cuts) == 2
    assert sum(c0 <= 60.0 and 64.0 <= c1 for c0, c1 in cuts) == 1  # o verso 12 está no segundo corte


def test_inicio_e_fim_nao_passam_da_musica():
    cuts = plan_cuts(song(10.0, [(0.2, 3.0), (3.5, 9.8)]), 30.0)
    assert cuts == [(0.0, 10.0)]


def test_verso_maior_que_o_alvo_vira_corte_proprio():
    assert plan_cuts(song(60.0, [(0.0, 40.0)]), 30.0) == [(0.0, 40.5)]


def test_corte_de_noventa_segundos_mantem_versos_inteiros():
    lines = [(i * 5.0, i * 5.0 + 4.0) for i in range(60)]  # 300 s de versos
    cuts = plan_cuts(song(300.0, lines), 90.0)
    assert len(cuts) >= 3
    for start, end in lines:
        assert sum(c0 <= start and end <= c1 for c0, c1 in cuts) == 1
    for c0, c1 in cuts:
        assert c1 - c0 <= 136.0  # o último corte curto junta com o anterior: até 1,5 × alvo


@pytest.mark.parametrize("exportar", [False, True])
def test_run_com_cortes_renderiza_todos_numa_chamada(tmp_path, monkeypatch, exportar):
    lines = [(i * 5.0, i * 5.0 + 4.0) for i in range(18)]
    data = song(100.0, lines)
    audio = tmp_path / "musica.mp3"
    audio.write_bytes(b"audio")
    lyrics = tmp_path / "letra.txt"
    lyrics.write_text("um\ndois", encoding="utf-8")
    monkeypatch.setattr(pipeline, "OUTPUT", tmp_path / "output")
    out = pipeline.OUTPUT / pipeline.make_slug(audio, "um\ndois")
    out.mkdir(parents=True)
    (out / "song.json").write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(pipeline, "_separate", lambda job: None)
    monkeypatch.setattr(pipeline, "_beats", lambda job: None)
    monkeypatch.setattr(pipeline, "_theme", lambda job: None)
    monkeypatch.setattr(pipeline, "_props", lambda job: None)
    rendered = []
    monkeypatch.setattr(pipeline, "render_all", lambda jobs: rendered.append([job.video.name for job in jobs]))
    exportados = []
    monkeypatch.setattr(pipeline, "export_all", lambda args, videos: exportados.append(videos))
    args = argparse.Namespace(audio=audio, lyrics=lyrics, style="karaoke", background="gradient", clip=None, format="vertical",
                              cuts=30.0, no_separate=False, skip_theme=False, force=False, model="small", language="pt",
                              export=exportar)
    assert pipeline.run(args) == 0
    esperados = [f"video-{pipeline.variant_name('karaoke', 'gradient', clip)}.mp4" for clip in plan_cuts(data, 30.0)]
    assert len(esperados) == 3
    assert rendered == [esperados]  # um lote com os três cortes
    variantes = [pipeline.variant_name("karaoke", "gradient", clip) for clip in plan_cuts(data, 30.0)]
    assert [variant for _, variant in exportados[0]] == variantes  # a exportação recebe um vídeo por corte


def test_cortes_recusa_zero_e_combinacao_com_clip():
    with pytest.raises(SystemExit):
        pipeline.main(["--audio", "a.mp3", "--lyrics", "a.txt", "--cuts", "0"])
    with pytest.raises(SystemExit):
        pipeline.main(["--audio", "a.mp3", "--lyrics", "a.txt", "--cuts", "30", "--clip", "0:10"])
