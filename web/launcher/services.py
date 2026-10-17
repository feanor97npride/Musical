# Serviços do iniciador: ler a URL do túnel, limitar os reinícios e ligar/desligar os processos.
import os
import re
import subprocess
import threading
import time
from collections import deque
from collections.abc import Callable, Mapping
from pathlib import Path

from web.launcher.windows import kill_tree

TUNNEL_URL = re.compile(r"https://([a-z0-9-]+)\.trycloudflare\.com", re.IGNORECASE)


def extract_tunnel_url(line: str) -> str | None:
    for match in TUNNEL_URL.finditer(line):
        if match.group(1).lower() != "api":  # api.trycloudflare.com aparece em mensagens de erro
            return match.group(0).lower()
    return None


class RestartPolicy:
    """Libera até `limit` reinícios dentro de `window` segundos."""

    def __init__(self, limit: int = 5, window: float = 60.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._limit = limit
        self._window = window
        self._clock = clock
        self._times: deque[float] = deque()

    def allow(self) -> bool:
        now = self._clock()
        while self._times and now - self._times[0] > self._window:
            self._times.popleft()
        if len(self._times) >= self._limit:
            return False
        self._times.append(now)
        return True


def child_env(env: Mapping[str, str]) -> dict[str, str]:
    # UTF-8 nos filhos: no Windows o padrão do pipe é cp1252 e o texto com acento quebraria
    return {**os.environ, **env, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}


class Service:
    """Um processo (servidor ou túnel) com a saída lida numa thread."""

    def __init__(self, name: str, argv: list[str], cwd: Path, env: Mapping[str, str],
                 on_line: Callable[[str, str], None]) -> None:
        self.name = name
        self.argv = argv
        self.cwd = cwd
        self.env = env
        self.on_line = on_line
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if os.name == "nt":
            extra = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        else:
            extra = {"start_new_session": True}
        self._proc = subprocess.Popen(
            self.argv, cwd=self.cwd, env=child_env(self.env), stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
            errors="replace", bufsize=1, **extra)
        self._thread = threading.Thread(target=self._pump, args=(self._proc,), daemon=True)
        self._thread.start()

    def _pump(self, proc: subprocess.Popen) -> None:
        for line in proc.stdout:
            self.on_line(self.name, line.rstrip())

    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def stop(self) -> None:
        if self._proc is not None:
            kill_tree(self._proc)
        if self._thread is not None:
            self._thread.join(2)  # um neto que sobreviveu não pode travar o encerramento
