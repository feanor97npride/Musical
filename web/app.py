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
from engine.props import BACKGROUNDS, SUBTITLE_STYLES as STYLES
from engine.write_lyrics import write_lyrics
from web import history
from web.biblioteca import build_router
from web.delivery import deliver_ready
from web.jobs import Job, JobQueue
from web.letra import build_router as letra_router
from web.pacote import build_pack, parse_draft

load_dotenv(ROOT / ".env")
MAX_BYTES = 25 * 1024 * 1024
MAX_IMAGE_BYTES = 10 * 1024 * 1024
CUTS = {"": None, "15": 15, "30": 30, "60": 60, "90": 90}  # segundos por corte; vazio = um vídeo só
STATIC = Path(__file__).resolve().parent / "static"
# senha opcional: sem ela, qualquer um que acessa o servidor usa (uso local)
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "").strip()
# sites que podem chamar o servidor de outra origem, ex.: a página no Cloudflare Pages
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()]
queue = JobQueue()
queue.on_ready = deliver_ready  # músicas da pasta do Drive são copiadas para a pasta de saída ao terminar


@asynccontextmanager
async def lifespan(_app: FastAPI):
    queue.start()
    yield


app = FastAPI(title="Lyric Video Generator", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)  # sem /docs pelo túnel
if ALLOWED_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["GET", "POST"],
                       allow_headers=["X-Access-Token"])


def _check_token(x_access_token: str | None = Header(None)) -> None:
    # compare_digest só aceita ASCII em str: em bytes, senha com acento não dá erro 500
    if ACCESS_TOKEN and not secrets.compare_digest((x_access_token or "").encode("utf-8"), ACCESS_TOKEN.encode("utf-8")):
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


async def _read_limited(upload: UploadFile, limit: int = MAX_BYTES) -> bytes:
    data = bytearray()
    while chunk := await upload.read(1024 * 1024):
        data.extend(chunk)
        if len(data) > limit:
            raise HTTPException(413, f"o arquivo passa do limite de {limit // (1024 * 1024)} MB")
    return bytes(data)


def _find(job_id: str) -> Job:
    job = queue.jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "job não encontrado")
    return job


def _check_options(style: str, background: str, cuts: str, video_format: str) -> None:
    if style not in STYLES:
        raise HTTPException(400, "estilo de legenda desconhecido")
    if background not in BACKGROUNDS:
        raise HTTPException(400, "fundo desconhecido")
    if cuts not in CUTS:
        raise HTTPException(400, "duração de corte desconhecida")
    if video_format not in ("vertical", "horizontal"):
        raise HTTPException(400, "formato desconhecido")


app.include_router(build_router(queue, _check_token, _check_options, CUTS))
app.include_router(letra_router(queue, _check_token, _find, _read_limited))


@app.post("/jobs", dependencies=[Depends(_check_token)])
async def create_job(audio: UploadFile = File(...), lyrics: str = Form(""), style: str = Form("karaoke"),
                     background: str = Form("gradient"), clip_start: str = Form(""), clip_end: str = Form(""),
                     cuts: str = Form(""), background_image: UploadFile | None = File(None),
                     video_format: str = Form("vertical", alias="format"), confirm: bool = Form(False),
                     draft: str = Form("")) -> dict:
    if not confirm:
        raise HTTPException(400, "confirme que a música é sua ou que você tem autorização para usá-la")
    try:
        texts = parse_draft(draft)  # textos da letra, para o pacote; vazio = sem eles
    except ValueError as error:
        raise HTTPException(400, f"textos para postar: {error}")
    if not (audio.filename or "").lower().endswith(".mp3"):
        raise HTTPException(400, "envie um arquivo .mp3")
    if not lyrics.strip():
        raise HTTPException(400, "a letra não pode estar vazia")
    _check_options(style, background, cuts, video_format)
    image = None
    if background == "image":
        suffix = Path(background_image.filename or "").suffix.lower() if background_image else ""
        if suffix not in (".jpg", ".jpeg", ".png"):
            raise HTTPException(400, "envie a imagem de fundo em JPG ou PNG")
        image = (await _read_limited(background_image, MAX_IMAGE_BYTES), suffix)
    clip = _clip(clip_start, clip_end)
    if CUTS[cuts] and clip:
        raise HTTPException(400, "use trecho ou cortes, não os dois")
    job = queue.create(audio.filename or "musica.mp3", await _read_limited(audio), lyrics, style, background, clip,
                       CUTS[cuts], image, video_format, texts)
    return {"id": job.id}


@app.get("/jobs/{job_id}", dependencies=[Depends(_check_token)])
def job_status(job_id: str) -> dict:
    return _find(job_id).to_dict()


@app.post("/jobs/{job_id}/variante", dependencies=[Depends(_check_token)])
def job_variant(job_id: str, video_format: str = Form("vertical", alias="format"), cuts: str = Form("")) -> dict:
    """Outro formato da mesma música, com a letra e o MP3 já enviados (preset full da página)."""
    job = _find(job_id)
    if video_format not in ("vertical", "horizontal"):
        raise HTTPException(400, "formato desconhecido")
    if cuts not in CUTS:
        raise HTTPException(400, "duração de corte desconhecida")
    if job.status != "done" or job.kind != "video":  # só copia música já processada (letra e jobs com erro não têm o MP3 pronto)
        raise HTTPException(409, "só dá para criar outro formato de um vídeo já pronto")
    return {"id": queue.clone(job, video_format, CUTS[cuts]).id}

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


@app.get("/jobs/{job_id}/pacote.zip", dependencies=[Depends(_check_token)])
def job_pack(job_id: str) -> FileResponse:
    job = _find(job_id)
    if job.status != "done" or not job.ready_videos:
        raise HTTPException(409, "o vídeo ainda não está pronto")
    return FileResponse(build_pack(job), media_type="application/zip", filename=f"{job.audio.stem}-pacote.zip")


@app.post("/lyrics", dependencies=[Depends(_check_token)])
def create_lyrics(context: str = Form("")) -> dict:
    # def, não async: a chamada à API leva segundos e o FastAPI roda a rota fora do laço do servidor
    try:
        draft = write_lyrics(context)
    except ValueError as error:
        raise HTTPException(400, str(error))
    except RuntimeError as error:
        raise HTTPException(503, str(error))
    return history.add(context, draft)  # a letra gerada fica no histórico, para não se perder


@app.get("/historico", dependencies=[Depends(_check_token)])
def history_list() -> list[dict]:
    return history.list_items()


@app.get("/historico/{item_id}", dependencies=[Depends(_check_token)])
def history_get(item_id: str) -> dict:
    item = history.get(item_id)
    if item is None:
        raise HTTPException(404, "item não encontrado no histórico")
    return item


@app.delete("/historico/{item_id}", dependencies=[Depends(_check_token)], status_code=204)
def history_delete(item_id: str) -> None:
    if not history.remove(item_id):
        raise HTTPException(404, "item não encontrado no histórico")


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
