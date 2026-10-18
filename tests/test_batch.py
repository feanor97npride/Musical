# Testes do lote: pares MP3 + letra, erro que não para o lote e opções repassadas a cada música. Sem render real.
import argparse

from engine import batch, pipeline


def make_folder(tmp_path):
    for name in ("b", "a", "c"):
        (tmp_path / f"{name}.mp3").write_bytes(b"audio")
    for name in ("a", "c"):  # "b" não tem letra: fica de fora
        (tmp_path / f"{name}.txt").write_text("um\ndois", encoding="utf-8")
    return tmp_path


def test_pares_sao_achados_em_ordem_e_sem_letra_fica_de_fora(tmp_path):
    folder = make_folder(tmp_path)
    assert [audio.name for audio, _ in batch.pairs(folder)] == ["a.mp3", "c.mp3"]


def test_erro_numa_musica_nao_para_as_outras(tmp_path, monkeypatch):
    folder = make_folder(tmp_path)

    def fake_run(args):
        if args.audio.name == "a.mp3":
            raise RuntimeError("falhou de propósito")
        return 0

    monkeypatch.setattr(pipeline, "run", fake_run)
    options = argparse.Namespace(style="karaoke", background="gradient", clip=None, cuts=None)
    results = batch.run_batch(folder, options)
    assert [(name, code) for name, code, _ in results] == [("a.mp3", 1), ("c.mp3", 0)]


def test_opcoes_chegam_a_cada_musica(tmp_path, monkeypatch):
    folder = make_folder(tmp_path)
    recebidos = []
    monkeypatch.setattr(pipeline, "run", lambda args: recebidos.append(args) or 0)
    monkeypatch.setattr(batch, "load_dotenv", lambda *_args, **_kwargs: None)
    code = batch.main(["--folder", str(folder), "--style", "oneword", "--clip", "0:10"])
    assert code == 0
    assert [args.audio.name for args in recebidos] == ["a.mp3", "c.mp3"]
    assert all(args.style == "oneword" and args.clip == (0.0, 10.0) for args in recebidos)


def test_pasta_sem_pares_devolve_erro(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "load_dotenv", lambda *_args, **_kwargs: None)
    assert batch.main(["--folder", str(tmp_path)]) == 1
