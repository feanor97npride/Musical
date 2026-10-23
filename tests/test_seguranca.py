# Testes de segurança e robustez do site: caminhos escondidos das mensagens, CORS do histórico e envio grande demais.
from fastapi.testclient import TestClient

from web import app as web_app
from web import limites, runner


def test_caminhos_com_espaco_e_relativos_saem_da_mensagem():
    assert runner.hide_paths(r"erro em C:\Users\Marcos Silva\a.mp3") == "erro em <caminho> <caminho>"
    assert runner.hide_paths(r"falhou em output\web\abc\x.mp3") == "falhou em <caminho>"
    assert runner.hide_paths("linha 39: 1/2 da música") == "linha 39: 1/2 da música"


def test_cors_libera_o_metodo_delete_do_historico():
    assert "DELETE" in web_app.CORS_METHODS  # o middleware só é criado com ALLOWED_ORIGINS, então testa a lista usada


def test_envio_grande_demais_e_recusado_antes_de_ler(monkeypatch):
    monkeypatch.setattr(limites, "MAX_REQUEST", 10)  # limite de teste: qualquer envio real passa disso
    with TestClient(web_app.app) as client:
        response = client.post("/letra", files={"audio": ("a.mp3", b"ID3fake", "audio/mpeg")})
    assert response.status_code == 413
