"""
Fixtures compartilhadas dos testes.

`tk_root`: dá um `tk.Tk()` fresco por teste, para caracterizar
`painel_controle.py`. Usa o `$DISPLAY` já disponível (sessão gráfica, X11
ou XWayland) se existir; senão sobe um `Xvfb` descartável uma única vez por
sessão de teste (mesma técnica usada para tirar screenshot headless do
painel nesta análise) e desliga no final. Se nem um nem outro estiver
disponível, os testes que dependem disto são PULADOS — não falham — para
não quebrar CI sem ambiente gráfico.
"""

import os
import shutil
import subprocess
import time

import pytest


def _tentar_tk():
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    return root


@pytest.fixture(scope="session")
def _display():
    if os.environ.get("DISPLAY"):
        try:
            r = _tentar_tk()
            r.destroy()
            yield
            return
        except Exception:
            pass

    xvfb_bin = shutil.which("Xvfb")
    if not xvfb_bin:
        pytest.skip("sem $DISPLAY e sem Xvfb instalado — não dá para testar a GUI aqui")

    display = f":{90000 + (os.getpid() % 1000)}"
    proc = subprocess.Popen(
        [xvfb_bin, display, "-screen", "0", "800x600x24"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    os.environ["DISPLAY"] = display
    time.sleep(0.8)  # dá tempo do Xvfb subir antes do primeiro Tk()

    try:
        r = _tentar_tk()
        r.destroy()
    except Exception as e:
        proc.terminate()
        pytest.skip(f"Xvfb subiu mas Tk não conseguiu conectar: {e}")
        return

    yield
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture
def tk_root(_display):
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass
