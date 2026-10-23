# Roda a pipeline (ou a transcrição) de um job num subprocess e lê o progresso do stdout.
import os
import subprocess
import sys
from typing import TYPE_CHECKING

from engine.pipeline import ROOT

if TYPE_CHECKING:
    from web.jobs import Job


def run_pipeline(job: "Job") -> int:
    command = [sys.executable, "-m", "engine.pipeline", "--audio", str(job.audio),
               "--lyrics", str(job.lyrics), "--style", job.style, "--background", job.background,
               "--format", job.format, "--export"]  # o pacote para postar usa a cópia exportada
    if job.clip:
        command += ["--clip", f"{job.clip[0]}:{job.clip[1]}"]
    if job.cuts:
        command += ["--cuts", str(job.cuts)]
    if job.background == "image":
        command += ["--background-image", str(job.background_image)]
    if job.kind == "letra":  # transcrição: troca o comando; as opções de vídeo acima não se aplicam
        command = [sys.executable, "-m", "engine.transcribe", "--audio", str(job.audio), "--out", str(job.transcript), "--force"]
    # no Windows o filho escreve em cp1252 por padrão; forçamos UTF-8 para o texto com acento não quebrar a leitura
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               encoding="utf-8", errors="replace",
                               env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"})
    for line in process.stdout:
        job.read_line(line.rstrip("\r\n"))
    return process.wait()
