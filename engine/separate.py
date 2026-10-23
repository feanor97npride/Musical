# Separação de vocais com Demucs por subprocess. A voz fica num cache por áudio: letras diferentes da mesma música reaproveitam.
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

VOICE_CACHE = Path(__file__).resolve().parents[1] / "output" / "voz"


def voice_dir(audio: Path) -> Path:
    """Pasta da voz deste MP3: o nome vem do conteúdo, não da letra (corrigir uma vírgula não refaz o Demucs)."""
    return VOICE_CACHE / hashlib.sha1(audio.read_bytes()).hexdigest()[:16]


def separate_vocals(audio: Path, out_dir: Path, force: bool = False) -> Path:
    target = out_dir / "vocals.wav"
    if target.exists() and not force:  # force refaz, mas só troca o arquivo quando o Demucs termina
        return target
    work = out_dir / "demucs"
    try:
        subprocess.run([sys.executable, "-m", "demucs", "--two-stems=vocals", "-o", str(work), str(audio)], check=True)
        produced = next(work.rglob("vocals.wav"), None)
        if produced is None:
            raise RuntimeError("o Demucs terminou sem gerar vocals.wav")
        out_dir.mkdir(parents=True, exist_ok=True)
        tmp = out_dir / "vocals.tmp.wav"
        shutil.copy(produced, tmp)
        os.replace(tmp, target)  # cópia parcial nunca vira o cache
    finally:
        shutil.rmtree(work, ignore_errors=True)  # os outros stems não são usados e ocupam bastante disco
    return target
