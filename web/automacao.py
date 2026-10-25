# Liga as automações do servidor: aviso no Telegram e Drive automático (cada uma só se estiver no .env).
import logging
import os
import threading

from web import avisos, drive_auto, telegram
from web.jobs import JobQueue

logger = logging.getLogger(__name__)


def start_automation(queue: JobQueue) -> None:
    if telegram.configured():
        threading.Thread(target=avisos.watch, args=(queue,), daemon=True).start()
    if drive_auto.enabled():
        if os.environ.get("DRIVE_INPUT_DIR", "").strip():
            threading.Thread(target=drive_auto.watch, args=(queue,), daemon=True).start()
        else:
            logger.error("DRIVE_AUTO ligado, mas DRIVE_INPUT_DIR está vazio: o Drive automático não começou")
