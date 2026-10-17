# Testes da parte pura dos serviços: URL do túnel e limite de reinícios.
from web.launcher.services import RestartPolicy, extract_tunnel_url


def test_acha_a_url_do_tunel_em_linha_com_ruido():
    linha = "2026-10-17 INF |  https://ABC-def.trycloudflare.com  |"
    assert extract_tunnel_url(linha) == "https://abc-def.trycloudflare.com"


def test_ignora_o_endereco_api_das_mensagens_de_erro():
    assert extract_tunnel_url("erro ao falar com https://api.trycloudflare.com") is None


def test_linha_sem_url_devolve_none():
    assert extract_tunnel_url("iniciando o túnel...") is None


def test_limite_de_reinicios_e_liberado_depois_da_janela():
    agora = [0.0]
    politica = RestartPolicy(limit=5, window=60.0, clock=lambda: agora[0])
    assert all(politica.allow() for _ in range(5))
    assert politica.allow() is False  # o sexto pedido dentro da janela é negado
    agora[0] = 61.0
    assert politica.allow() is True  # passou a janela, libera de novo
