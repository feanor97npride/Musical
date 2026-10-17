# Parte pura dos serviços: ler a URL do túnel e limitar os reinícios.
import re
import time
from collections import deque
from collections.abc import Callable

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
