# Testes da cópia para postar: argumentos do ffmpeg, nome, falha sem trocar nada, cache e checagem antecipada. Sem ffmpeg real.
import argparse
import os
import subprocess
import time
from pathlib import Path

import pytest

from engine import export, pipeline


def fake_ffmpeg(monkeypatch, calls: list, fail: bool = False) -> None:
    monkeypatch.setattr(export.shutil, "which", lambda name: "/usr/bin/ffmpeg")

    def run(cmd, check):
        calls.append(cmd)
        Path(cmd[-1]).write_bytes(b"saida")  # o último argumento é o arquivo temporário
        if fail:
            raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(export.subprocess, "run", run)


def make_video(folder: Path, name: str = "video-karaoke-gradient.mp4") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    video = folder / name
    video.write_bytes(b"fonte")
    return video


def make_copia(video: Path, when: float) -> Path:
    copia = video.parent / "para-postar" / export.export_name(Path("a.mp3"), "karaoke-gradient")
    copia.parent.mkdir(exist_ok=True)
    copia.write_bytes(b"pronta")
    os.utime(copia, (when, when))
    return copia


def test_nome_sem_acento_e_com_variante():
    assert export.export_name(Path("Tua Presença Presença.mp3"), "karaoke-aurora-0-10") == \
        "tua-presenca-presenca-karaoke-aurora-0-10.mp4"


def test_ffmpeg_recebe_os_ajustes_de_postagem(tmp_path, monkeypatch):
    src = make_video(tmp_path)
    dst = tmp_path / "saida.mp4"
    calls = []
    fake_ffmpeg(monkeypatch, calls)
    export.export(src, dst)
    cmd = calls[0]

    def valor(flag: str) -> str:
        return cmd[cmd.index(flag) + 1]

    assert valor("-i") == str(src)
    assert valor("-c:v") == "libx264"
    assert valor("-pix_fmt") == "yuv420p"
    assert valor("-maxrate") == export.MAX_RATE
    assert valor("-bufsize") == export.BUF_SIZE
    assert valor("-b:a") == "128k"
    assert valor("-movflags") == "+faststart"
    assert dst.read_bytes() == b"saida"
    assert not (tmp_path / "saida.tmp.mp4").exists()


def test_falha_do_ffmpeg_mantem_a_copia_anterior(tmp_path, monkeypatch):
    src = make_video(tmp_path)
    dst = tmp_path / "saida.mp4"
    dst.write_bytes(b"antigo")
    fake_ffmpeg(monkeypatch, [], fail=True)
    with pytest.raises(subprocess.CalledProcessError):
        export.export(src, dst)
    assert dst.read_bytes() == b"antigo"
    assert not (tmp_path / "saida.tmp.mp4").exists()


def test_sem_ffmpeg_avisa_com_clareza(tmp_path, monkeypatch):
    monkeypatch.setattr(export.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="ffmpeg não encontrado"):
        export.export(make_video(tmp_path), tmp_path / "saida.mp4")


def test_sem_ffmpeg_recusa_antes_do_render(monkeypatch):
    monkeypatch.setattr(export.shutil, "which", lambda name: None)
    with pytest.raises(SystemExit):
        pipeline.main(["--audio", "a.mp3", "--lyrics", "a.txt", "--export"])


def test_export_vem_desligado_por_padrao():
    assert pipeline.build_options().parse_args([]).export is False


def test_sem_export_nao_roda_ffmpeg(tmp_path, monkeypatch):
    monkeypatch.setattr(export, "export", lambda src, dst: pytest.fail("não devia rodar"))
    args = argparse.Namespace(audio=tmp_path / "a.mp3", export=False, force=False)
    assert export.export_all(args, [(make_video(tmp_path), "karaoke-gradient")]) == "desligado (sem --export)"


def test_copia_pulada_quando_ja_esta_mais_nova_que_tudo(tmp_path, monkeypatch):
    video = make_video(tmp_path)
    os.utime(video, (1000, 1000))
    make_copia(video, time.time() + 100)  # mais nova que o vídeo e que este arquivo de código
    monkeypatch.setattr(export, "export", lambda src, dst: pytest.fail("não devia rodar"))
    assert export.export_video(video, Path("a.mp3"), "karaoke-gradient", force=False) == "pulado (cache)"


def test_copia_refeita_quando_o_video_muda(tmp_path, monkeypatch):
    video = make_video(tmp_path)
    agora = time.time()
    copia = make_copia(video, agora + 100)
    os.utime(video, (agora + 200, agora + 200))
    fake_ffmpeg(monkeypatch, [])
    assert export.export_video(video, Path("a.mp3"), "karaoke-gradient", force=False) is None
    assert copia.read_bytes() == b"saida"


def test_copia_refeita_quando_os_ajustes_do_codigo_mudam(tmp_path, monkeypatch):
    video = make_video(tmp_path)
    os.utime(video, (1000, 1000))
    make_copia(video, 2000)  # mais antiga que este arquivo de código: MAX_RATE pode ter mudado
    calls = []
    fake_ffmpeg(monkeypatch, calls)
    assert export.export_video(video, Path("a.mp3"), "karaoke-gradient", force=False) is None
    assert len(calls) == 1


def test_cada_corte_tem_sua_copia(tmp_path, monkeypatch):
    videos = [(make_video(tmp_path, f"video-karaoke-gradient-{i}-{i + 30}.mp4"), f"karaoke-gradient-{i}-{i + 30}")
              for i in (0, 30)]
    calls = []
    fake_ffmpeg(monkeypatch, calls)
    args = argparse.Namespace(audio=Path("Minha Música.mp3"), export=True, force=False)
    assert export.export_all(args, videos) is None
    assert len(calls) == 2
    finais = sorted(p.name for p in (tmp_path / "para-postar").iterdir())
    assert finais == ["minha-musica-karaoke-gradient-0-30.mp4", "minha-musica-karaoke-gradient-30-60.mp4"]


def test_nome_do_pacote_com_partes_e_video_unico():
    audio = Path("O Deserto Vai Florir.mp3")
    assert export.part_name(audio, 1, 1) == "o-deserto-vai-florir.mp4"
    assert export.part_name(audio, 1, 10) == "01-o-deserto-vai-florir-parte-1-de-10.mp4"
    assert export.part_name(audio, 10, 10) == "10-o-deserto-vai-florir-parte-10-de-10.mp4"


def test_copia_para_postar_fica_na_pasta_para_postar_do_video():
    video = Path("output/o-deserto/video-karaoke-gradient-0-10.mp4")
    assert export.exported_path(video, Path("O Deserto.mp3")) == Path(
        "output/o-deserto/para-postar/o-deserto-karaoke-gradient-0-10.mp4")
