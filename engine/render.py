# Render dos cortes em uma só execução do renderer (um bundle e um navegador para o lote inteiro).
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "renderer"


def _cached(job) -> bool:
    unchanged = job.props.exists() and job.props.read_text(encoding="utf-8") == job.new_props
    return unchanged and job.video.exists() and not job.args.force


def render_all(jobs: list) -> str | None:
    """Renderiza os trechos que mudaram, numa chamada só. Quem já tem cache não entra no lote."""
    stale = [job for job in jobs if not _cached(job)]
    if not stale:
        return "pulado (cache)"
    npm = shutil.which("npm")  # no Windows é npm.CMD; sem o caminho completo o Windows não acha
    if npm is None:
        raise RuntimeError("npm não encontrado: instale o Node.js 18 ou superior")
    # um nome temporário por trecho: os cortes da mesma música dividem a pasta de saída
    manifest = []
    for job in stale:
        tmp_props, tmp_video = job.props.with_suffix(".tmp.json"), job.video.with_suffix(".tmp.mp4")
        tmp_props.write_text(job.new_props, encoding="utf-8")
        manifest.append({"props": str(tmp_props), "video": str(tmp_video),
                         "finalProps": str(job.props), "finalVideo": str(job.video)})
    manifest_path = stale[0].out / "render-lote.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    try:
        subprocess.run([npm, "run", "render-batch", "--", str(manifest_path)], cwd=RENDERER, check=True)
    finally:
        for entry in manifest:  # o que sobrou de um render que falhou some; os arquivos finais ficam como estavam
            Path(entry["props"]).unlink(missing_ok=True)
            Path(entry["video"]).unlink(missing_ok=True)
        manifest_path.unlink(missing_ok=True)
    return None
