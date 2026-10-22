# Testes do lote de render: um só comando para os cortes, sem os que já têm cache, e um nome temporário por corte.
import argparse
import json
from pathlib import Path

from engine import pipeline, render


def corte(tmp_path: Path, clip: tuple[float, float]) -> pipeline.Job:
    args = argparse.Namespace(audio=tmp_path / "musica.mp3", style="karaoke", background="gradient", clip=clip,
                              format="vertical", force=False)
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)  # os cortes de uma música dividem a mesma pasta de saída
    job = pipeline.Job(args, "um\ndois", out)
    job.new_props = f"props {clip}"
    return job


def test_cortes_viram_um_so_comando_e_quem_tem_cache_fica_de_fora(tmp_path, monkeypatch):
    comandos, manifestos = [], []
    monkeypatch.setattr(render.shutil, "which", lambda name: "/usr/bin/npm")

    def run(cmd, cwd, check):
        comandos.append(cmd)
        manifesto = json.loads(Path(cmd[-1]).read_text(encoding="utf-8"))
        manifestos.append(manifesto)
        for entry in manifesto:  # o que o render-batch.mjs faz com cada corte
            Path(entry["video"]).write_bytes(b"novo")
            Path(entry["video"]).replace(entry["finalVideo"])
            Path(entry["props"]).replace(entry["finalProps"])

    monkeypatch.setattr(render.subprocess, "run", run)
    cortes = [corte(tmp_path, (0.0, 10.0)), corte(tmp_path, (10.0, 20.0)), corte(tmp_path, (20.0, 30.0))]
    cortes[0].props.write_text(cortes[0].new_props, encoding="utf-8")  # primeiro corte já está pronto
    cortes[0].video.write_bytes(b"ja pronto")

    assert render.render_all(cortes) is None
    assert len(comandos) == 1 and comandos[0][1:4] == ["run", "render-batch", "--"]
    assert [entry["finalVideo"] for entry in manifestos[0]] == [str(job.video) for job in cortes[1:]]
    assert len({entry["video"] for entry in manifestos[0]}) == 2  # um temporário por corte, sem colisão
    assert [job.video.read_bytes() for job in cortes[1:]] == [b"novo", b"novo"]
    assert cortes[0].video.read_bytes() == b"ja pronto"


def test_so_cortes_com_cache_nao_chama_o_npm(tmp_path, monkeypatch):
    def boom(*_args, **_kwargs):
        raise AssertionError("não devia chamar o npm")

    monkeypatch.setattr(render.subprocess, "run", boom)
    job = corte(tmp_path, (0.0, 10.0))
    job.props.write_text(job.new_props, encoding="utf-8")
    job.video.write_bytes(b"mp4")
    assert render.render_all([job]) == "pulado (cache)"
