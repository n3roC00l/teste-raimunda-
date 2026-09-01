"""
Caracterização da GUI do painel (Tkinter) — trava o comportamento ATUAL.
Escrito antes do `refactor/ui-split` (que prometia "layout igual") contra
`painel_controle.App`; agora exercita `ui.painel.App`, o novo lugar da
classe — o split moveu o código de `App.__init__` para `ui/widgets.py` e
`ui/tema.py`, sem trocar nenhuma classe Tk, cor ou texto. Este arquivo
passar sem alteração de asserts é a prova de que a promessa foi cumprida.
`painel_controle.py` virou um shim (`from ui.painel import App, main`) só
para o `iniciar_aplicacao.sh` continuar funcionando.

Roda com uma App Tkinter de verdade (fixture `tk_root`, ver conftest.py),
não com um simulacro — só `subprocess.Popen` e as caixas de diálogo modais
são substituídos por dublês: sem isso, `App.__init__` tentaria abrir o
analisador de verdade, e qualquer `messagebox` trava o teste esperando
clique.

Rodar:  python -m pytest tests/test_characterization_painel.py -q
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui import painel as pc
from core import status as status_mod


class FakePopen:
    """Dublê de subprocess.Popen — não abre processo nenhum de verdade."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.stdout = None
        self.terminated = False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        pass


@pytest.fixture(autouse=True)
def sem_subprocessos_nem_dialogos_reais(monkeypatch):
    monkeypatch.setattr(pc.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(pc.messagebox, "showerror", lambda *a, **k: None)
    monkeypatch.setattr(pc.messagebox, "showwarning", lambda *a, **k: None)
    monkeypatch.setattr(pc.messagebox, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(pc.messagebox, "askyesno", lambda *a, **k: False)
    monkeypatch.setattr(pc.messagebox, "askokcancel", lambda *a, **k: True)


@pytest.fixture
def app(tk_root, tmp_path, monkeypatch):
    # status isolado por teste — não lê/escreve o status_analise.json real
    monkeypatch.setattr(pc.config, "ARQUIVO_STATUS", str(tmp_path / "status.json"))
    a = pc.App(tk_root)
    yield a


# ---------------------------------------------------------------------------
# Estado inicial (o que o operador vê ao abrir o painel)
# ---------------------------------------------------------------------------
def test_titulo_da_janela_usa_a_versao_do_config(app, tk_root):
    assert tk_root.title() == f"Estação de Controlo de Captura v{pc.config.VERSAO} - Rover FAPA"


def test_widgets_iniciais_pinados(app):
    assert app.lbl_plant_count.cget("text") == "--"
    assert app.lbl_total_count.cget("text") == "0"
    assert app.lbl_current_operacao.cget("text") == "Parado"
    assert app.btn_start_stop.cget("text") == "▶ INICIAR CAPTURA"
    assert app.btn_sync.cget("text") == "☁ SINCRONIZAR NUVEM"
    assert app.btn_exit.cget("text") == "SAIR DO PAINEL"
    assert app.entry_tratamento.cget("state") == "normal"
    assert app.entry_linha.cget("state") == "normal"


def test_analisador_e_disparado_na_abertura(app):
    assert isinstance(app.analyzer_process, FakePopen)
    assert app.analyzer_process.args[0][1] == pc.config.SCRIPT_ANALISADOR


# ---------------------------------------------------------------------------
# start_capture / stop_capture
# ---------------------------------------------------------------------------
def test_start_capture_sem_campos_mostra_erro_e_nao_inicia(app, monkeypatch):
    chamadas = []
    monkeypatch.setattr(pc.messagebox, "showerror", lambda *a, **k: chamadas.append(a))

    app.start_capture()

    assert chamadas, "deveria ter chamado messagebox.showerror"
    assert app.is_running is False
    assert app.capturador_process is None


def test_start_capture_monta_setor_e_atualiza_estado(app):
    app.entry_tratamento.insert(0, "Tratamento A")
    app.entry_linha.insert(0, "1")

    app.start_capture()

    assert app.is_running is True
    assert app.setor_atual == "trat_Tratamento_A_linha_1"  # espaço -> "_" (pinado)
    assert app.btn_start_stop.cget("text") == "⏹ PARAR CAPTURA"
    assert app.entry_tratamento.cget("state") == "disabled"
    assert app.entry_linha.cget("state") == "disabled"
    assert app.lbl_current_operacao.cget("text") == "trat_Tratamento_A_linha_1"
    assert app.lbl_total_count.cget("text") == "0"
    assert app.lbl_plant_count.cget("text") == "--"
    assert isinstance(app.capturador_process, FakePopen)
    assert "--setor" in app.capturador_process.args[0]


def test_stop_capture_reverte_o_estado(app):
    app.entry_tratamento.insert(0, "A")
    app.entry_linha.insert(0, "1")
    app.start_capture()
    capturador = app.capturador_process

    app.stop_capture()

    assert app.is_running is False
    assert app.btn_start_stop.cget("text") == "▶ INICIAR CAPTURA"
    assert app.lbl_current_operacao.cget("text") == "Parado"
    assert app.entry_tratamento.cget("state") == "normal"
    assert capturador.terminated is True


# ---------------------------------------------------------------------------
# update_dashboard — o coração do bug corrigido em refactor/status-schema
# ---------------------------------------------------------------------------
def test_dashboard_mostra_total_quando_status_bate_com_a_parcela_corrente(app):
    app.entry_tratamento.insert(0, "A")
    app.entry_linha.insert(0, "1")
    app.start_capture()  # setor_atual = "trat_A_linha_1"

    status_mod.escrever(app.status_file, status_mod.StatusAnalise(
        parcela="trat_A_linha_1", plantulas_corrigido=45, total_parcela_corrigido=321,
    ))
    app.update_dashboard()

    assert app.lbl_plant_count.cget("text") == "45"
    assert app.lbl_total_count.cget("text") == "321"


def test_dashboard_nao_mostra_total_de_outra_parcela_enquanto_captura(app):
    app.entry_tratamento.insert(0, "A")
    app.entry_linha.insert(0, "1")
    app.start_capture()  # setor_atual = "trat_A_linha_1"

    status_mod.escrever(app.status_file, status_mod.StatusAnalise(
        parcela="trat_B_linha_9", total_parcela_corrigido=999,
    ))
    app.update_dashboard()

    assert app.lbl_total_count.cget("text") == "0"  # não vazou o total da outra parcela


def test_dashboard_com_status_pre_schema_v20_nao_quebra_e_nao_atualiza(app):
    with open(app.status_file, "w") as f:
        json.dump({"ultima_imagem_analisada": "x.jpg", "plantulas_detectadas_ia": 5}, f)

    app.update_dashboard()  # não deve levantar

    assert app.lbl_plant_count.cget("text") == "--"  # ler() -> None, label intocado


def test_dashboard_sem_arquivo_de_status_nao_quebra(app):
    assert not os.path.exists(app.status_file)
    app.update_dashboard()
    assert app.lbl_plant_count.cget("text") == "--"


# ---------------------------------------------------------------------------
# exit_app
# ---------------------------------------------------------------------------
def test_exit_app_confirmado_encerra_os_processos(app, monkeypatch):
    monkeypatch.setattr(pc.messagebox, "askokcancel", lambda *a, **k: True)
    analyzer = app.analyzer_process

    app.exit_app()

    assert analyzer.terminated is True
