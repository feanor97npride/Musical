# Limites de envio: recusa o corpo grande antes de lê-lo, e confere o tamanho de cada arquivo ao lê-lo.
from fastapi import HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

MAX_BYTES = 25 * 1024 * 1024  # MP3
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # imagem de fundo
MAX_VIDEO_BYTES = 100 * 1024 * 1024  # vídeo com a música (MP4)
MAX_REQUEST = 110 * 1024 * 1024  # shortcut: vídeo + letra num envio; subir se o vídeo passar de 100 MB


async def read_limited(upload: UploadFile, limit: int = MAX_BYTES) -> bytes:
    data = bytearray()
    while chunk := await upload.read(1024 * 1024):
        data.extend(chunk)
        if len(data) > limit:
            raise HTTPException(413, f"o arquivo passa do limite de {limit // (1024 * 1024)} MB")
    return bytes(data)


async def check_request_size(request: Request, call_next):
    size = request.headers.get("content-length", "0")
    if size.isdigit() and int(size) > MAX_REQUEST:  # recusa antes de o corpo ser lido, mesmo sem senha
        return JSONResponse({"detail": "envio grande demais: o limite é 110 MB"}, status_code=413)
    return await call_next(request)
