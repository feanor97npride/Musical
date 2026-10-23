# Rotas da biblioteca: músicas da pasta do Google Drive sincronizada no PC (DRIVE_INPUT_DIR).
import os
from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException

from web.jobs import JobQueue
from web.library import list_songs, load_song


def library_root() -> Path:
    """Pasta de entrada do Drive (DRIVE_INPUT_DIR). Sem ela, a biblioteca não existe."""
    value = os.environ.get("DRIVE_INPUT_DIR", "").strip()
    if not value:
        raise HTTPException(404, "pasta do Drive não configurada: preencha DRIVE_INPUT_DIR no .env")
    root = Path(value)
    if not root.is_dir():
        raise HTTPException(409, "pasta do Drive não encontrada: confira se o Google Drive está sincronizado no PC")
    return root


def build_router(queue: JobQueue, check_token: Callable, check_options: Callable[[str, str, str, str], None],
                 cuts: dict[str, int | None]) -> APIRouter:
    router = APIRouter()

    @router.get("/biblioteca", dependencies=[Depends(check_token)])
    def library_songs() -> dict:
        return {"songs": list_songs(library_root())}

    @router.post("/biblioteca/{name}/jobs", dependencies=[Depends(check_token)])
    def library_job(name: str, style: str = Form("karaoke"), background: str = Form("gradient"), cuts_value: str = Form("", alias="cuts"),
                    video_format: str = Form("vertical", alias="format"), confirm: bool = Form(False)) -> dict:
        """Gera uma música da pasta do Drive. A autorização continua obrigatória, como no envio pelo formulário."""
        if not confirm:
            raise HTTPException(400, "confirme que a música é sua ou que você tem autorização para usá-la")
        check_options(style, background, cuts_value, video_format)
        song = load_song(library_root(), name)
        if song is None:
            raise HTTPException(404, "música não encontrada: a pasta precisa de exatamente um MP3 e um TXT")
        audio, lyrics, image = song
        if not lyrics.strip():
            raise HTTPException(400, "a letra da pasta está vazia")
        if background == "image" and image is None:
            raise HTTPException(400, "a pasta não tem fundo.jpg ou fundo.png para o fundo Minha imagem")
        job = queue.create(f"{name}.mp3", audio, lyrics, style, background, None, cuts[cuts_value], image, video_format,
                           library_name=name)
        return {"id": job.id}

    return router
