"""
Testes de core/watchdog.py — sd_notify opcional.
"""

import importlib
import os
import socket
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _recarregar():
    import core.watchdog as w
    return importlib.reload(w)


def test_sem_notify_socket_e_no_op(monkeypatch):
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    w = _recarregar()
    assert w.ativo() is False
    assert w.pronto() is False
    assert w.batida() is False
    assert w.status("x") is False


def test_com_notify_socket_manda_ready_e_watchdog(tmp_path, monkeypatch):
    sockpath = str(tmp_path / "notify.sock")
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    srv.bind(sockpath)
    srv.settimeout(2)
    monkeypatch.setenv("NOTIFY_SOCKET", sockpath)

    w = _recarregar()
    assert w.ativo() is True

    assert w.pronto() is True
    assert srv.recv(64) == b"READY=1"

    assert w.batida() is True
    assert srv.recv(64) == b"WATCHDOG=1"

    assert w.status("analisando") is True
    assert srv.recv(64) == b"STATUS=analisando"

    srv.close()


def test_socket_sumido_nao_levanta(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTIFY_SOCKET", str(tmp_path / "nao_existe.sock"))
    w = _recarregar()
    assert w.batida() is False  # não levanta


@pytest.fixture(autouse=True)
def _restaura_modulo():
    yield
    import core.watchdog
    importlib.reload(core.watchdog)
