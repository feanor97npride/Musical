# Testes do fluxo n8n: o JSON abre, toda ligação aponta para um bloco que existe e nada sensível fica no arquivo.
import json
import re
from pathlib import Path

FLOW = Path(__file__).resolve().parents[1] / "docs" / "n8n" / "aviso-video-pronto.json"
ROUTES = {"audio", "lyrics", "confirm", "style", "background", "format", "cuts"}  # campos que POST /jobs aceita


def flow() -> dict:
    return json.loads(FLOW.read_text(encoding="utf-8"))


def test_json_abre_e_tem_os_blocos_esperados():
    names = {node["name"] for node in flow()["nodes"]}
    assert {"Enviar música", "Montar envios", "Enviar para o servidor", "Guardar envio", "Pronto?", "Avisar pronto"} <= names


def test_toda_ligacao_aponta_para_um_bloco_que_existe():
    data = flow()
    names = {node["name"] for node in data["nodes"]}
    for source, outputs in data["connections"].items():
        assert source in names, source
        for branch in outputs["main"]:
            for link in branch:
                assert link["node"] in names, link["node"]


def test_envio_manda_so_campos_que_a_rota_aceita():
    send = next(node for node in flow()["nodes"] if node["name"] == "Enviar para o servidor")
    sent = {param["name"] for param in send["parameters"]["bodyParameters"]["parameters"]}
    assert sent <= ROUTES, sent - ROUTES


def test_atalho_do_formulario_tem_as_opcoes_certas():
    form = next(node for node in flow()["nodes"] if node["name"] == "Enviar música")
    field = next(f for f in form["parameters"]["formFields"]["values"] if f["fieldLabel"] == "atalho")
    assert [option["option"] for option in field["fieldOptions"]["values"]] == ["TikTok", "YouTube", "Full"]


def test_nenhum_token_ou_senha_no_arquivo():
    text = FLOW.read_text(encoding="utf-8")
    assert not re.search(r"\d{6,}:[A-Za-z0-9_-]{20,}", text)  # formato de token do bot do Telegram
    assert "ACCESS_TOKEN=" not in text and "N8N_ENCRYPTION_KEY=" not in text
