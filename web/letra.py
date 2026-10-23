# Rotas da letra pelo áudio: envia o MP3, acompanha pelo /jobs e baixa o texto gerado para revisão.
from collections.abc import Callable

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from web.jobs import Job, JobQueue
from web.launcher.windows import kill_tree


def build_router(queue: JobQueue, check_token: Callable, find: Callable[[str], Job],
                 read_limited: Callable) -> APIRouter:
    router = APIRouter()

    @router.post("/jobs/{job_id}/cancelar", dependencies=[Depends(check_token)])
    def cancel_job(job_id: str) -> dict:
        """Cancela um envio na fila ou em andamento: o processo morre e o job termina com erro."""
        job = find(job_id)
        if job.status in ("done", "error"):
            raise HTTPException(409, "este envio já terminou")
        job.cancelled, job.message = True, "cancelado pelo usuário"
        if job.process is not None:
            kill_tree(job.process)
        return {"ok": True}

    @router.post("/letra", dependencies=[Depends(check_token)])
    async def transcribe_job(audio: UploadFile = File(...)) -> dict:
        """Gera o texto da letra pelo áudio. O usuário revisa o texto antes de gerar o vídeo."""
        if not (audio.filename or "").lower().endswith(".mp3"):
            raise HTTPException(400, "envie um arquivo .mp3")
        return {"id": queue.create_letra(audio.filename, await read_limited(audio)).id}

    @router.get("/jobs/{job_id}/letra", dependencies=[Depends(check_token)])
    def job_letra(job_id: str) -> FileResponse:
        job = find(job_id)
        if job.status != "done" or job.kind != "letra":
            raise HTTPException(409, "a letra ainda não está pronta")
        return FileResponse(job.transcript, media_type="text/plain; charset=utf-8")

    return router
