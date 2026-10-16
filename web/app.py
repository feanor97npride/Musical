# Web mínima com FastAPI: envio de MP3 + letra, progresso por job e download do MP4.
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from web.jobs import Job, JobQueue

MAX_BYTES = 25 * 1024 * 1024
STYLES = {"highlight", "oneword", "karaoke"}
STATIC = Path(__file__).resolve().parent / "static"
queue = JobQueue()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    queue.start()
    yield


app = FastAPI(title="Lyric Video Generator", lifespan=lifespan)


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


@app.post("/jobs")
async def create_job(audio: UploadFile = File(...), lyrics: str = Form(""), style: str = Form("karaoke"),
                     clip_start: str = Form(""), clip_end: str = Form(""), confirm: bool = Form(False)) -> dict:
    if not confirm:
        raise HTTPException(400, "confirme que a música é sua ou que você tem autorização para usá-la")
    if not (audio.filename or "").lower().endswith(".mp3"):
        raise HTTPException(400, "envie um arquivo .mp3")
    if not lyrics.strip():
        raise HTTPException(400, "a letra não pode estar vazia")
    if style not in STYLES:
        raise HTTPException(400, "estilo de legenda desconhecido")
    clip = _clip(clip_start, clip_end)
    job = queue.create(audio.filename or "musica.mp3", await _read_limited(audio), lyrics, style, clip)
    return {"id": job.id}


@app.get("/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    return _find(job_id).to_dict()


@app.get("/jobs/{job_id}/video")
def job_video(job_id: str) -> FileResponse:
    job = _find(job_id)
    if job.status != "done" or job.video is None:
        raise HTTPException(409, "o vídeo ainda não está pronto")
    return FileResponse(job.video, media_type="video/mp4")


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
