# Web mínima com FastAPI: envio de MP3 + letra, progresso por job e download do MP4.
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from engine.pipeline import ROOT
from web.jobs import Job, JobQueue

load_dotenv(ROOT / ".env")
MAX_BYTES = 25 * 1024 * 1024
STYLES = {"highlight", "oneword", "karaoke"}
BACKGROUNDS = {"gradient", "solid", "aurora", "aurora-gl", "sunrise"}
CUTS = {"": None, "15": 15, "30": 30, "60": 60}  # segundos por corte; vazio = um vídeo só
STATIC = Path(__file__).resolve().parent / "static"
# senha opcional: sem ela, qualquer um que acessa o servidor usa (uso local)
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "").strip()
# sites que podem chamar o servidor de outra origem, ex.: a página no Cloudflare Pages
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()]
queue = JobQueue()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    queue.start()
    yield


app = FastAPI(title="Lyric Video Generator", lifespan=lifespan)
if ALLOWED_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["GET", "POST"],
                       allow_headers=["X-Access-Token"])


def _check_token(x_access_token: str | None = Header(None)) -> None:
    if ACCESS_TOKEN and not secrets.compare_digest(x_access_token or "", ACCESS_TOKEN):
        raise HTTPException(401, "senha de acesso incorreta")


def _clip(start: str, end: str) -> tuple[float, float] | None:
    if not start and not end:
        return None
    try:
        begin, finish = float(start), float(end)
    except ValueError:
        raise HTTPException(400, "início e fim do trecho devem ser números em segundos")
    if not 0 <= begin < finish:
        raise HTTPException(400, "o trecho precisa começar em 0 ou depois e terminar depois do início")
    return begin, finish


async def _read_limited(upload: UploadFile) -> bytes:
    data = bytearray()
    while chunk := await upload.read(1024 * 1024):
        data.extend(chunk)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "o arquivo passa do limite de 25 MB")
    return bytes(data)


def _find(job_id: str) -> Job:
    job = queue.jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "job não encontrado")
    return job


@app.post("/jobs", dependencies=[Depends(_check_token)])
async def create_job(audio: UploadFile = File(...), lyrics: str = Form(""), style: str = Form("karaoke"),
                     background: str = Form("gradient"), clip_start: str = Form(""), clip_end: str = Form(""),
                     cuts: str = Form(""), confirm: bool = Form(False)) -> dict:
    if not confirm:
        raise HTTPException(400, "confirme que a música é sua ou que você tem autorização para usá-la")
    if not (audio.filename or "").lower().endswith(".mp3"):
        raise HTTPException(400, "envie um arquivo .mp3")
    if not lyrics.strip():
        raise HTTPException(400, "a letra não pode estar vazia")
    if style not in STYLES:
        raise HTTPException(400, "estilo de legenda desconhecido")
    if background not in BACKGROUNDS:
        raise HTTPException(400, "fundo desconhecido")
    if cuts not in CUTS:
        raise HTTPException(400, "duração de corte desconhecida")
    clip = _clip(clip_start, clip_end)
    if CUTS[cuts] and clip:
        raise HTTPException(400, "use trecho ou cortes, não os dois")
    job = queue.create(audio.filename or "musica.mp3", await _read_limited(audio), lyrics, style, background, clip,
                       CUTS[cuts])
    return {"id": job.id}


@app.get("/jobs/{job_id}", dependencies=[Depends(_check_token)])
def job_status(job_id: str) -> dict:
    return _find(job_id).to_dict()


@app.get("/jobs/{job_id}/video", dependencies=[Depends(_check_token)])
def job_video(job_id: str, n: int | None = None) -> FileResponse:
    job = _find(job_id)
    if job.status != "done" or job.video is None:
        raise HTTPException(409, "o vídeo ainda não está pronto")
    if n is None:
        if len(job.ready_videos) > 1:
            raise HTTPException(400, "este job tem cortes: informe o número do corte em n")
        n = 0
    if not 0 <= n < len(job.ready_videos):  # só os arquivos da lista do job; o cliente não escolhe caminho
        raise HTTPException(404, "corte não encontrado")
    return FileResponse(job.ready_videos[n], media_type="video/mp4")


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
