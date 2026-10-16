# Separação de vocais com Demucs por subprocess; reaproveita vocals.wav se já existir.
import shutil
import subprocess
import sys
from pathlib import Path


def separate_vocals(audio: Path, out_dir: Path, force: bool = False) -> Path:
    target = out_dir / "vocals.wav"
    if target.exists() and not force:  # force refaz, mas só troca o arquivo quando o Demucs termina
        return target
    work = out_dir / "demucs"
    subprocess.run([sys.executable, "-m", "demucs", "--two-stems=vocals", "-o", str(work), str(audio)], check=True)
    produced = next(work.rglob("vocals.wav"))
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(produced, target)
    shutil.rmtree(work)  # os outros stems não são usados e ocupam bastante disco
    return target
