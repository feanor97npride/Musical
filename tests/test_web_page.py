# Testes da página estática: os IDs que o JavaScript usa existem no HTML, e o favicon e a fonte estão na página.
import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "web" / "static"


def test_ids_usados_pelo_script_existem_no_html():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    scripts = (STATIC / "app.js").read_text(encoding="utf-8") + (STATIC / "lyrics.js").read_text(encoding="utf-8")
    used = set(re.findall(r'getElementById\("([^"]+)"\)', scripts)) | set(re.findall(r'data-copy="([^"]+)"', html))
    assert used, "nenhum ID encontrado: o padrão da busca mudou"
    assert [name for name in used if f'id="{name}"' not in html] == []


def test_pagina_tem_favicon_e_fontes():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert 'rel="icon"' in html
    assert "fonts.googleapis.com/css2?family=Bricolage+Grotesque" in html
