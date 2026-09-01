"""
Caracterização da GUI do painel (Tkinter) — golden master atual.

Histórico: nasceu antes do `refactor/ui-split`; sobreviveu ao split; foi
reajustado no `feat/ui-v1` (visual novo) e agora no `feat/parcela` (parcela
estruturada + navegação + progresso do plot). O que **não** muda é o
comportamento essencial: máquina de estados de captura, regra do TOTAL por
parcela, robustez a status ausente/pré-schema.

Roda com uma App Tkinter de verdade (fixture `tk_root`, ver conftest.py) —
só `subprocess`, `messagebox` e `simpledialog` são substituídos por dublês.

Rodar:  python -m pytest tests/test_characterization_painel.py -q
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui import painel as pc
from ui import tema
from core import status as status_mod


class FakePopen:
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
def sem_efeitos_reais(monkeypatch):
    monkeypatch.setattr(pc.subprocess, "Popen", FakePopen)

    def _nao_e_rpi(*a, **k):
        raise FileNotFoundError("vcgencmd")
    monkeypatch.setattr(pc.subprocess, "check_output", _nao_e_rpi)

    monkeypatch.setattr(pc.messagebox, "showerror", lambda *a, **k: None)
    monkeypatch.setattr(pc.messagebox, "showwarning", lambda *a, **k: None)
    monkeypatch.setattr(pc.messagebox, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(pc.messagebox, "askyesno", lambda *a, **k: False)
    monkeypatch.setattr(pc.messagebox, "askokcancel", lambda *a, **k: True)
    monkeypatch.setattr(pc.simpledialog, "askstring", lambda *a, **k: None)


@pytest.fixture
def app(tk_root, tmp_path, monkeypatch):
    monkeypatch.setattr(pc.config, "ARQUIVO_STATUS", str(tmp_path / "status.json"))
    monkeypatch.setattr(pc.config, "ARQUIVO_PARCELA", str(tmp_path / "parcela.json"))
    monkeypatch.setattr(pc.config, "ARQUIVO_ULTIMA_SYNC", str(tmp_path / "sync.txt"))
    monkeypatch.setattr(pc.config, "PLANILHA_PROGRAMACAO", str(tmp_path / "sem_planilha.csv"))
    a = pc.App(tk_root)
    yield a


# ---------------------------------------------------------------------------
# Estado inicial
# ---------------------------------------------------------------------------
def test_titulo_da_janela_usa_a_versao_do_config(app, tk_root):
    assert tk_root.title() == f"Estação de Controlo de Captura v{pc.config.VERSAO} - Rover FAPA"


def test_faixa_da_parcela_reflete_o_navegador(app):
    assert app.nav.modo == "manual"                       # sem planilha nos testes
    assert app._am["val_x"].cget("text") == "1"
    assert app._am["val_y"].cget("text") == "1"
    assert app._am["val_linha"].cget("text") == "1"
    assert app._am["lbl_ident"].cget("text") == "X1Y1L1"
    assert app._am["lbl_exp"].cget("text") == pc.config.EXPERIMENTO_PADRAO


def test_widgets_iniciais_pinados(app):
    assert app.lbl_total_count.cget("text") == "0"
    assert app.lbl_bruto.cget("text") == "--"
    assert app.lbl_fila.cget("text") == "0"
    assert app.btn_start_stop.cget("text") == "▶ Iniciar Captura · F5"
    assert app.btn_sync.cget("text") == "☁ Sincronizar · F9"


def test_atalhos_de_teclado_ligados(app):
    assert app.root.bind("<F5>")
    assert app.root.bind("<F9>")
    assert app.root.bind("<F2>")
    assert app.root.bind("<Control-q>")


def test_analisador_e_disparado_na_abertura(app):
    assert isinstance(app.analyzer_process, FakePopen)
    assert app.analyzer_process.args[0][1] == pc.config.SCRIPT_ANALISADOR


# ---------------------------------------------------------------------------
# navegação da parcela
# ---------------------------------------------------------------------------
def test_proxima_anda_linha_e_persiste(app):
    app.parcela_proxima()
    assert app._am["lbl_ident"].cget("text") == "X1Y1L2"
    assert app._am["val_linha"].cget("text") == "2"
    assert os.path.exists(pc.config.ARQUIVO_PARCELA)  # salvou


def test_anterior_volta(app):
    app.parcela_proxima()
    app.parcela_proxima()   # X1Y1L3
    app.parcela_anterior()  # X1Y1L2
    assert app._am["lbl_ident"].cget("text") == "X1Y1L2"


def test_editar_experimento(app, monkeypatch):
    monkeypatch.setattr(pc.simpledialog, "askstring", lambda *a, **k: "Ensaio Pinhão 2026")
    app.editar_experimento()
    assert app.nav.experimento == "Ensaio Pinhão 2026"
    assert app._am["lbl_exp"].cget("text") == "Ensaio Pinhão 2026"


def test_navegacao_bloqueada_durante_captura(app):
    app.start_capture()
    ident_antes = app._am["lbl_ident"].cget("text")
    app.parcela_proxima()
    assert app._am["lbl_ident"].cget("text") == ident_antes
    assert str(app._am["btn_prox"].cget("state")) == "disabled"


# ---------------------------------------------------------------------------
# start_capture / stop_capture
# ---------------------------------------------------------------------------
def test_start_capture_usa_o_identificador_do_navegador(app):
    app.parcela_proxima()  # X1Y1L2
    app.start_capture()

    assert app.is_running is True
    assert app.setor_atual == "X1Y1L2"
    assert app.btn_start_stop.cget("text") == "⏹ Parar Captura · F5"
    assert app.lbl_total_count.cget("text") == "0"
    assert isinstance(app.capturador_process, FakePopen)
    assert list(app.capturador_process.args[0])[-2:] == ["--setor", "X1Y1L2"]


def test_stop_capture_reverte_o_estado(app):
    app.start_capture()
    capturador = app.capturador_process
    app.stop_capture()

    assert app.is_running is False
    assert app.btn_start_stop.cget("text") == "▶ Iniciar Captura · F5"
    assert str(app._am["btn_prox"].cget("state")) == "normal"
    assert capturador.terminated is True


# ---------------------------------------------------------------------------
# update_dashboard
# ---------------------------------------------------------------------------
def test_dashboard_total_da_linha_e_fila(app):
    app.start_capture()  # setor_atual = X1Y1L1

    status_mod.escrever(app.status_file, status_mod.StatusAnalise(
        parcela="X1Y1L1", plot="X1Y1", linha=1,
        plantulas_bruto=137, plantulas_corrigido=139,
        total_parcela_corrigido=139, total_linha_1=139,
        fila_pendente=3,
    ))
    app.update_dashboard()

    assert app.lbl_total_count.cget("text") == "139"
    assert app.lbl_bruto.cget("text") == "137"
    assert app.lbl_fila.cget("text") == "3 a analisar"
    assert app.lbl_fila.cget("fg") == tema.WARN


def test_dashboard_progresso_do_plot(app):
    # navegador no plot X1Y1, linha 2
    app.parcela_proxima()
    status_mod.escrever(app.status_file, status_mod.StatusAnalise(
        plot="X1Y1", linha=2, total_linha_1=41, total_linha_2=15, total_linha_3=0,
    ))
    app.update_dashboard()

    linhas = app._pg["linhas"]
    assert linhas[0]["val"].cget("text") == "41"
    assert linhas[1]["val"].cget("text") == "15"
    assert linhas[2]["val"].cget("text") == "—"
    assert linhas[1]["atual"].cget("text") == "● atual"   # nav.linha == 2
    assert app._pg["lbl_total_plot"].cget("text") == "56"


def test_dashboard_progresso_ignora_status_de_outro_plot(app):
    # navegador em X1Y1; status é de X9Y9
    status_mod.escrever(app.status_file, status_mod.StatusAnalise(
        plot="X9Y9", linha=1, total_linha_1=99,
    ))
    app.update_dashboard()
    assert app._pg["linhas"][0]["val"].cget("text") == "—"
    assert app._pg["lbl_total_plot"].cget("text") == "0"


def test_dashboard_nao_mostra_total_de_outra_parcela_enquanto_captura(app):
    app.start_capture()  # setor_atual = X1Y1L1
    status_mod.escrever(app.status_file, status_mod.StatusAnalise(
        parcela="X9Y9L1", total_parcela_corrigido=999,
    ))
    app.update_dashboard()
    assert app.lbl_total_count.cget("text") == "0"


def test_dashboard_com_status_pre_schema_nao_quebra(app):
    with open(app.status_file, "w") as f:
        json.dump({"ultima_imagem_analisada": "x.jpg", "plantulas_detectadas_ia": 5}, f)
    app.update_dashboard()  # não deve levantar
    assert app.lbl_bruto.cget("text") == "--"


def test_dashboard_sem_status_nao_quebra(app):
    assert not os.path.exists(app.status_file)
    app.update_dashboard()
    assert "aguardando" in app._pill["texto"].cget("text")


def test_pilula_e_estado_do_sistema(app):
    status_mod.escrever(app.status_file, status_mod.StatusAnalise(analisador_estado="pronto"))
    app.update_dashboard()
    assert app._pill["texto"].cget("text").strip() == "sistema pronto"
    assert app._est["val_analisador"].cget("text") == "pronto"
    assert app._est["val_captura"].cget("text") == "parada"

    app.start_capture()
    app.update_dashboard()
    assert app._pill["texto"].cget("text").strip() == "capturando"
    assert app._est["val_captura"].cget("text") == "ativa"


def test_rodape_mostra_versao_e_disco(app):
    app.update_dashboard()
    rod = app._est["lbl_rodape"].cget("text")
    assert f"v{pc.config.VERSAO}" in rod
    assert "Disco" in rod


# ---------------------------------------------------------------------------
# exit_app
# ---------------------------------------------------------------------------
def test_exit_app_confirmado_encerra_os_processos(app, monkeypatch):
    monkeypatch.setattr(pc.messagebox, "askokcancel", lambda *a, **k: True)
    analyzer = app.analyzer_process
    app.exit_app()
    assert analyzer.terminated is True
