# Etapas da pipeline: cada uma imprime "[n/total] nome... resultado"; uma falha vira StepError.
import time
from collections.abc import Callable

TOTAL_STEPS = 6


class StepError(Exception):
    def __init__(self, label: str, cause: Exception) -> None:
        super().__init__(f"etapa '{label}' falhou: {cause}")
        self.label = label
        self.cause = cause


def run_step(number: int, label: str, action: Callable[[], str | None]) -> None:
    print(f"[{number}/{TOTAL_STEPS}] {label}... ", end="", flush=True)
    began = time.monotonic()
    try:
        note = action()
    except Exception as error:
        print("falhou")
        raise StepError(label, error) from error
    print(note or f"ok ({time.monotonic() - began:.0f} s)")
