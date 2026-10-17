# Testes das verificações do iniciador: endereços, porta, senha e cloudflared.
from web.launcher.checks import normalize_origin, preflight


def sem_porta_ocupada(_port: int) -> bool:
    return False


def com_cloudflared(_env) -> str:
    return "/usr/bin/cloudflared"


def test_normaliza_origem_tirando_barra_caminho_e_maiusculas():
    assert normalize_origin("https://Site.vercel.app/x/") == "https://site.vercel.app"


def test_origem_invalida_vira_texto_vazio():
    assert normalize_origin("site.vercel.app") == ""
    assert normalize_origin("ftp://site.vercel.app") == ""


def test_porta_ocupada_aborta():
    plan = preflight({"ACCESS_TOKEN": "x"}, in_use=lambda _port: True, finder=com_cloudflared)
    assert "já está em uso" in plan.abort


def test_porta_que_nao_e_numero_aborta():
    plan = preflight({"PORT": "abc"}, in_use=sem_porta_ocupada, finder=com_cloudflared)
    assert "número" in plan.abort


def test_token_vazio_desliga_o_tunel():
    plan = preflight({"ACCESS_TOKEN": ""}, in_use=sem_porta_ocupada, finder=com_cloudflared)
    assert plan.cloudflared is None
    assert any("NÃO será aberto" in aviso for aviso in plan.warnings)


def test_com_token_mantem_o_tunel():
    plan = preflight({"ACCESS_TOKEN": "senha"}, in_use=sem_porta_ocupada, finder=com_cloudflared)
    assert plan.cloudflared == "/usr/bin/cloudflared"


def test_site_fora_de_allowed_origins_avisa():
    env = {"ACCESS_TOKEN": "x", "SITE_URL": "https://a.vercel.app", "ALLOWED_ORIGINS": "https://b.vercel.app"}
    plan = preflight(env, in_use=sem_porta_ocupada, finder=com_cloudflared)
    assert any("ALLOWED_ORIGINS" in aviso for aviso in plan.warnings)


def test_site_dentro_de_allowed_origins_nao_avisa():
    env = {"ACCESS_TOKEN": "x", "SITE_URL": "https://a.vercel.app/",
           "ALLOWED_ORIGINS": "https://b.vercel.app, https://a.vercel.app"}
    plan = preflight(env, in_use=sem_porta_ocupada, finder=com_cloudflared)
    assert plan.site_url == "https://a.vercel.app"
    assert not any("ALLOWED_ORIGINS" in aviso for aviso in plan.warnings)


def test_sem_chave_do_tema_avisa_mas_nao_bloqueia():
    plan = preflight({"ACCESS_TOKEN": "x"}, in_use=sem_porta_ocupada, finder=com_cloudflared)
    assert any("THEME_API_KEY" in aviso for aviso in plan.warnings)
    assert plan.abort == ""


def test_com_chave_do_tema_nao_avisa():
    plan = preflight({"ACCESS_TOKEN": "x", "THEME_API_KEY": "chave"}, in_use=sem_porta_ocupada, finder=com_cloudflared)
    assert not any("THEME_API_KEY" in aviso for aviso in plan.warnings)


def test_sem_cloudflared_segue_so_local_com_aviso():
    plan = preflight({"ACCESS_TOKEN": "x"}, in_use=sem_porta_ocupada, finder=lambda _env: None)
    assert plan.cloudflared is None
    assert plan.abort == ""
    assert any("winget" in aviso for aviso in plan.warnings)


def test_token_do_tunel_sem_endereco_aborta():
    plan = preflight({"ACCESS_TOKEN": "x", "TUNNEL_TOKEN": "t"}, in_use=sem_porta_ocupada, finder=com_cloudflared)
    assert "TUNNEL_HOSTNAME" in plan.abort


def test_token_e_endereco_definem_o_tunel_fixo():
    env = {"ACCESS_TOKEN": "x", "TUNNEL_TOKEN": "t", "TUNNEL_HOSTNAME": "Whimsical.musicas.space"}
    plan = preflight(env, in_use=sem_porta_ocupada, finder=com_cloudflared)
    assert plan.abort == ""
    assert plan.tunnel_host == "whimsical.musicas.space"


def test_endereco_sem_token_e_ignorado_com_aviso():
    env = {"ACCESS_TOKEN": "x", "TUNNEL_HOSTNAME": "whimsical.musicas.space"}
    plan = preflight(env, in_use=sem_porta_ocupada, finder=com_cloudflared)
    assert plan.tunnel_host == ""
    assert any("ignorado" in aviso for aviso in plan.warnings)
