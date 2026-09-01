"""
core/watchdog.py — integração opcional com o watchdog do systemd (sd_notify).

Se o processo roda sob um serviço systemd `Type=notify` com `WatchdogSec`,
estas funções avisam o systemd que o processo (a) terminou de subir e
(b) continua vivo. Se o processo hang, o systemd reinicia.

Fora do systemd (rodando à mão, ou sem `NOTIFY_SOCKET` no ambiente), tudo
aqui é **no-op** — não faz nada e não quebra.

Protocolo sd_notify implementado direto no socket, sem depender do pacote
`python3-systemd`.

Ref.: sd_notify(3), systemd.service(5). docs/MELHORIAS.md frente #3.
"""

import os
import socket

_ADDR = os.environ.get("NOTIFY_SOCKET")
_sock = None


def ativo():
    return bool(_ADDR)


def _enviar(mensagem):
    global _sock
    if not _ADDR:
        return False
    try:
        if _sock is None:
            _sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        destino = _ADDR
        if destino.startswith("@"):          # namespace abstrato
            destino = "\0" + destino[1:]
        _sock.sendto(mensagem.encode("utf-8"), destino)
        return True
    except OSError:
        return False


def pronto():
    """READY=1 — inicialização concluída (necessário com Type=notify)."""
    return _enviar("READY=1")


def batida():
    """WATCHDOG=1 — 'estou vivo'. Chame bem mais rápido que o WatchdogSec."""
    return _enviar("WATCHDOG=1")


def status(texto):
    """STATUS=… — texto livre que aparece no `systemctl status`."""
    return _enviar("STATUS=" + texto)
