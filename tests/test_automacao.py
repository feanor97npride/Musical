# Testes de quem liga as automações: nada sobe sem configuração, e cada uma sobe só com a sua.
from web import automacao, avisos, drive_auto
from web.jobs import JobQueue


class ThreadFalsa:
    iniciadas: list = []

    def __init__(self, target, args, daemon):
        self.target = target

    def start(self) -> None:
        ThreadFalsa.iniciadas.append(self.target)


def preparar(monkeypatch):
    ThreadFalsa.iniciadas = []
    monkeypatch.setattr(automacao.threading, "Thread", ThreadFalsa)


def test_sem_configuracao_nenhuma_thread_sobe(monkeypatch):
    preparar(monkeypatch)
    automacao.start_automation(JobQueue())
    assert ThreadFalsa.iniciadas == []


def test_telegram_configurado_liga_so_os_avisos(monkeypatch):
    preparar(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:x")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    automacao.start_automation(JobQueue())
    assert ThreadFalsa.iniciadas == [avisos.watch]


def test_drive_auto_com_pasta_liga_o_vigia(monkeypatch):
    preparar(monkeypatch)
    monkeypatch.setenv("DRIVE_AUTO", "1")
    monkeypatch.setenv("DRIVE_INPUT_DIR", "C:/Drive/Musicas")
    automacao.start_automation(JobQueue())
    assert ThreadFalsa.iniciadas == [drive_auto.watch]


def test_drive_auto_sem_pasta_de_entrada_nao_liga_e_avisa(monkeypatch, caplog):
    preparar(monkeypatch)
    monkeypatch.setenv("DRIVE_AUTO", "1")
    automacao.start_automation(JobQueue())
    assert ThreadFalsa.iniciadas == []
    assert "DRIVE_INPUT_DIR" in caplog.text
