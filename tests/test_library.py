# Testes da pasta do Drive: quais músicas aparecem e o que é lido de cada uma.
from pathlib import Path

from web.library import list_songs, load_song


def make_song(root: Path, name: str, files: list[str]) -> None:
    folder = root / name
    folder.mkdir(parents=True)
    for file in files:
        (folder / file).write_bytes(b"x")


def test_pasta_com_um_mp3_e_um_txt_entra(tmp_path):
    make_song(tmp_path, "Musica A", ["musica.mp3", "letra.txt"])
    assert list_songs(tmp_path) == ["Musica A"]


def test_pasta_com_dois_mp3_ou_sem_txt_fica_de_fora(tmp_path):
    make_song(tmp_path, "Dois mp3", ["a.mp3", "b.mp3", "letra.txt"])
    make_song(tmp_path, "Sem letra", ["musica.mp3"])
    assert list_songs(tmp_path) == []


def test_pasta_que_nao_existe_da_lista_vazia(tmp_path):
    assert list_songs(tmp_path / "nao-existe") == []


def test_imagem_opcional_e_lida_com_a_extensao_em_minusculas(tmp_path):
    make_song(tmp_path, "Com fundo", ["musica.mp3", "letra.txt", "fundo.JPG"])
    audio, lyrics, picture = load_song(tmp_path, "Com fundo")
    assert audio == b"x" and lyrics == "x"
    assert picture == (b"x", ".jpg")


def test_nome_que_sai_da_pasta_e_recusado(tmp_path):
    make_song(tmp_path, "Musica A", ["musica.mp3", "letra.txt"])
    assert load_song(tmp_path, "..") is None
    assert load_song(tmp_path, "../Musica A") is None
    assert load_song(tmp_path, "") is None
