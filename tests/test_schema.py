# Testes do contrato song.json: validate_song() e ida e volta com as dataclasses.
from engine.schema import Song, validate_song


def valid_song() -> dict:
    return {
        "version": 1,
        "language": "pt",
        "audio": {"file": "musica.mp3", "duration": 10.0, "bpm": 96.0},
        "lines": [
            {
                "id": 0, "text": "Primeiro verso", "section": "verse", "start": 1.0, "end": 2.5,
                "words": [
                    {"text": "Primeiro", "start": 1.0, "end": 1.5},
                    {"text": "verso", "start": 1.5, "end": 2.5},
                ],
            },
            {
                "id": 1, "text": "Segundo", "section": "chorus", "start": 3.0, "end": 4.0,
                "words": [{"text": "Segundo", "start": 3.0, "end": 4.0}],
            },
        ],
        "theme": None,
    }


def test_song_valido_nao_tem_erros():
    assert validate_song(valid_song()) == []


def test_tema_valido_nao_tem_erros():
    song = valid_song()
    song["theme"] = {
        "title": "Saudade no fim da tarde", "mood": "melancólico", "keywords": ["saudade"],
        "palette": ["#1B1B3A", "#693668", "#A74482"], "font": "Playfair Display",
        "visual_concept": "Gradiente lento",
    }
    assert validate_song(song) == []


def test_tempos_fora_de_ordem_entre_linhas():
    song = valid_song()
    song["lines"][1]["start"] = 0.5
    song["lines"][1]["words"][0]["start"] = 0.5
    errors = validate_song(song)
    assert errors == ["linha 1: start menor que o da linha anterior"]


def test_palavras_fora_de_ordem_dentro_da_linha():
    song = valid_song()
    song["lines"][0]["words"] = [
        {"text": "Primeiro", "start": 1.5, "end": 1.7},
        {"text": "verso", "start": 1.0, "end": 2.5},
    ]
    errors = validate_song(song)
    assert any("palavra 1" in error and "anterior" in error for error in errors)


def test_id_repetido():
    song = valid_song()
    song["lines"][1]["id"] = 0
    assert validate_song(song) == ["linha 1: id deve ser 1 (sequencial a partir de 0)"]


def test_secao_invalida():
    song = valid_song()
    song["lines"][0]["section"] = "refrao"
    assert any(error.startswith("linha 0: section") for error in validate_song(song))


def test_tempo_acima_da_duracao_respeita_tolerancia_de_005():
    song = valid_song()
    song["lines"][1]["end"] = 10.04
    song["lines"][1]["words"][0]["end"] = 10.04
    assert validate_song(song) == []
    song["lines"][1]["end"] = 10.2
    song["lines"][1]["words"][0]["end"] = 10.2
    assert any("duração" in error for error in validate_song(song))


def test_start_da_linha_diferente_da_primeira_palavra():
    song = valid_song()
    song["lines"][0]["start"] = 1.2
    assert validate_song(song) == ["linha 0: start e end devem ser os da primeira e da última palavra"]


def test_tema_com_fonte_e_paleta_invalidas():
    song = valid_song()
    song["theme"] = {
        "title": "T", "mood": "m", "keywords": [], "palette": ["#000000", "#FFFFFF"],
        "font": "Arial", "visual_concept": "v",
    }
    errors = validate_song(song)
    assert any(error.startswith("theme.palette") for error in errors)
    assert any(error.startswith("theme.font") for error in errors)


def test_entrada_malformada_devolve_erros_sem_quebrar():
    song = valid_song()
    song["lines"][0]["section"] = ["verse"]
    song["lines"][0]["words"] = "não é lista"
    bad_inputs = [None, [], {}, {"lines": "x"}, song]
    for bad in bad_inputs:
        assert validate_song(bad), f"deveria reprovar: {bad!r}"


def test_cores_hexadecimais_de_3_4_6_e_8_digitos_sao_aceitas():
    song = valid_song()
    song["theme"] = {
        "title": "T", "mood": "m", "keywords": [], "font": "Inter", "visual_concept": "v",
        "palette": ["#000", "#FFF8", "#1B1B3A", "#A74482FF"],
    }
    assert validate_song(song) == []


def test_cor_fora_do_formato_hexadecimal_e_recusada():
    song = valid_song()
    song["theme"] = {
        "title": "T", "mood": "m", "keywords": [], "font": "Inter", "visual_concept": "v",
        "palette": ["#GGG", "#12", "#1234567"],
    }
    assert any(error.startswith("theme.palette") for error in validate_song(song))


def test_version_1_ponto_zero_e_aceita_e_outro_numero_nao():
    song = valid_song()
    song["version"] = 1.0
    assert validate_song(song) == []
    song["version"] = 2
    assert any(error.startswith("version") for error in validate_song(song))


def test_bpm_precisa_ser_maior_que_zero():
    for bpm in (0, -120.0):
        song = valid_song()
        song["audio"]["bpm"] = bpm
        assert validate_song(song) == ["audio.bpm deve ser um número maior que zero"]


def test_numeros_absurdos_nao_lancam_excecao():
    huge = valid_song()
    huge["audio"]["duration"] = 10**400
    nan = valid_song()
    nan["lines"][0]["start"] = float("nan")
    assert validate_song(huge) and validate_song(nan)


def test_ida_e_volta_com_dataclasses():
    data = valid_song()
    assert Song.from_dict(data).to_dict() == data
