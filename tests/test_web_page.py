# Testes da página estática: IDs usados pelo JavaScript, referências de acessibilidade, botões de copiar e opções de rádio.
import re
from pathlib import Path

from web.app import BACKGROUNDS, CUTS, STYLES

STATIC = Path(__file__).resolve().parents[1] / "web" / "static"
HTML = (STATIC / "index.html").read_text(encoding="utf-8")


def test_ids_usados_pelo_script_existem_no_html():
    scripts = "".join((STATIC / name).read_text(encoding="utf-8")
                      for name in ("app.js", "entrega.js", "forms.js", "lyrics.js", "presets.js"))
    used = set(re.findall(r'getElementById\("([^"]+)"\)', scripts)) | set(re.findall(r'data-copy="([^"]+)"', HTML))
    assert used, "nenhum ID encontrado: o padrão da busca mudou"
    assert [name for name in used if f'id="{name}"' not in HTML] == []


def test_alvos_de_aria_existem_no_html():
    targets = {i for value in re.findall(r'aria-(?:describedby|errormessage|labelledby)="([^"]+)"', HTML) for i in value.split()}
    assert targets, "nenhuma referência de aria encontrada: o padrão da busca mudou"
    assert [name for name in targets if f'id="{name}"' not in HTML] == []


def test_botoes_de_copiar_tem_nomes_diferentes():
    buttons = re.findall(r"<button[^>]*data-copy=[^>]*>(.*?)</button>", HTML)
    names = [re.sub(r"<[^>]+>", "", text).strip() for text in buttons]
    assert len(names) >= 6
    assert len(set(names)) == len(names), names  # o mesmo nome para botões diferentes confunde o leitor de tela


def test_opcoes_de_radio_batem_com_o_que_o_servidor_aceita():
    def values(name: str) -> list[str]:
        return re.findall(rf'<input type="radio" id="[^"]+" name="{name}" value="([^"]*)"', HTML)

    assert set(values("style")) == STYLES
    assert set(values("background")) == BACKGROUNDS
    assert set(values("cuts")) == set(CUTS)
    assert set(values("format")) == {"vertical", "horizontal"}


def test_cada_grupo_de_radio_comeca_com_uma_opcao_marcada():
    checked = re.findall(r'<input type="radio" id="[^"]+" name="(\w+)" value="([^"]*)" checked>', HTML)
    assert sorted(checked) == [("background", "gradient"), ("cuts", ""), ("format", "vertical"), ("style", "karaoke")]


def test_pagina_tem_favicon_fontes_e_esquema_de_cores():
    assert 'rel="icon"' in HTML
    assert "fonts.googleapis.com/css2?family=Bricolage+Grotesque" in HTML
    assert '<meta name="color-scheme" content="light dark">' in HTML


def test_arquivos_locais_tem_versao_para_nao_ficar_em_cache():
    refs = re.findall(r'(?:href|src)="([^":/]+\.(?:css|js))(\?v=\d+)?"', HTML)
    assert len(refs) == 6, refs  # style.css, app.js, entrega.js, presets.js, forms.js, lyrics.js
    assert [name for name, version in refs if not version] == []
    assert [name for name, _ in refs if not (STATIC / name).exists()] == []


def test_rodape_linka_termos_e_privacidade():
    for name in ("termos.html", "privacidade.html"):
        assert f'href="{name}"' in HTML
        assert (STATIC / name).exists()
