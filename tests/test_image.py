# Imagem de fundo por IA: prompt do tema, chamada à API com resposta falsa e corte para 9:16.
import base64
import json
import shutil
import subprocess

import httpx
import pytest

from engine import image

PNG = base64.b64encode(b"\x89PNG fake").decode()


def fake_post(status=200, body=None):
    def post(url, **kwargs):
        assert "x-goog-api-key" in kwargs["headers"]
        return httpx.Response(status, json=body if body is not None else {})
    return post


def reply(*parts):
    return {"candidates": [{"content": {"parts": list(parts)}}]}


def test_prompt_usa_descricao_e_tema():
    theme = {"visual_concept": "praia ao amanhecer", "mood": "calmo", "keywords": ["mar", "sol", "areia"]}
    prompt = image.build_prompt(theme, "uma ponte")
    assert "uma ponte" in prompt and "praia ao amanhecer" in prompt and "mar, sol, areia" in prompt
    assert "sem texto" in prompt


def test_prompt_sem_descricao_nem_tema_ainda_tem_regras():
    prompt = image.build_prompt(None, "  ")
    assert "sem logotipos" in prompt


def test_devolve_a_imagem_da_resposta():
    body = reply({"text": "aqui"}, {"inlineData": {"mimeType": "image/png", "data": PNG}})
    assert image.generate_image("x", "chave", post=fake_post(body=body)) == b"\x89PNG fake"


def test_ignora_partes_de_pensamento():
    body = reply({"inlineData": {"data": PNG}, "thought": True},
                 {"inlineData": {"data": base64.b64encode(b"final").decode()}})
    assert image.generate_image("x", "chave", post=fake_post(body=body)) == b"final"


def test_erro_da_api_nao_mostra_a_chave():
    with pytest.raises(image.ImageError) as info:
        image.generate_image("x", "chave-secreta", post=fake_post(status=403, body={"error": "x"}))
    assert "403" in str(info.value) and "chave-secreta" not in str(info.value)


def test_resposta_sem_imagem_vira_erro_claro():
    with pytest.raises(image.ImageError, match="não devolveu imagem"):
        image.generate_image("x", "chave", post=fake_post(body=reply({"text": "não posso"})))
    with pytest.raises(image.ImageError, match="não devolveu imagem"):
        image.generate_image("x", "chave", post=fake_post(body={}))


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="precisa do ffmpeg")
def test_corta_para_1080_por_1920(tmp_path):
    png = tmp_path / "src.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=red:s=640x360",
                    "-frames:v", "1", str(png)], check=True)
    out = tmp_path / "background.jpg"
    image.save_background(png.read_bytes(), out)
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height", "-of", "json", str(out)], capture_output=True, text=True, check=True)
    stream = json.loads(probe.stdout)["streams"][0]
    assert (stream["width"], stream["height"]) == (1080, 1920)
    assert not out.with_suffix(".raw").exists()


def test_reaproveita_a_imagem_com_o_mesmo_prompt(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setenv("GEMINI_API_KEY", "chave")
    monkeypatch.setattr(image, "generate_image", lambda prompt, key: calls.append(prompt) or b"raw")
    monkeypatch.setattr(image, "save_background", lambda raw, out: out.write_bytes(raw))
    song = {"theme": None, "lines": []}
    first = image.ensure_background(tmp_path, song, "", False)
    second = image.ensure_background(tmp_path, song, "", False)
    assert first == second and len(calls) == 1
    image.ensure_background(tmp_path, song, "outra coisa", False)  # prompt diferente: gera de novo
    assert len(calls) == 2


def test_sem_chave_avisa_sem_chamar_a_api(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(image, "generate_image", lambda prompt, key: pytest.fail("não devia chamar a API"))
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        image.ensure_background(tmp_path, {"theme": None}, "", False)
