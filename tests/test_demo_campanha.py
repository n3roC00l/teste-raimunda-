"""
Testes de ferramentas/demo_campanha.py: a campanha sintética da visão 3D.

Roda o script num subprocesso (ele ajusta ROVER_BASE_DIR antes de importar o
config, então não pode rodar dentro do processo dos testes).
"""

import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(RAIZ, "ferramentas", "demo_campanha.py")


def _rodar(*args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, timeout=120)


def test_snapshot_estatico_e_marcado_como_demo(tmp_path):
    saida = tmp_path / "snapshot.json"
    r = _rodar("--dir", str(tmp_path / "demo"), "--snapshot", str(saida))
    assert r.returncode == 0, r.stderr
    s = json.loads(saida.read_text(encoding="utf-8"))
    assert s["demo"] is True
    assert "DEMO" in s["experimento"]
    assert len(s["campo"]["plots"]) == 216
    assert s["rover"]["capturando"] is True and s["rover"]["posicao"]
    # as anomalias plantadas aparecem como alerta
    alertas = {p["id"]: p["alerta"] for p in s["campo"]["plots"] if p["alerta"]}
    assert alertas.get("X4Y12") == "critico"      # carreira zerada
    assert alertas.get("X2Y15") == "atencao"      # dupla contagem
    assert (tmp_path / "demo" / "logs_analise" / "DEMO").exists()


def test_reprodutivel_com_a_mesma_semente(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    _rodar("--dir", str(tmp_path / "da"), "--snapshot", str(a))
    _rodar("--dir", str(tmp_path / "db"), "--snapshot", str(b))
    assert json.loads(a.read_text())["kpis"] == json.loads(b.read_text())["kpis"]


def test_recusa_pasta_com_dados_reais(tmp_path):
    logs = tmp_path / "rover" / "logs_analise"
    logs.mkdir(parents=True)
    (logs / "log_analise_total.csv").write_text("experimento,parcela\nreal,X1Y1L1\n")
    r = _rodar("--dir", str(tmp_path / "rover"), "--snapshot", str(tmp_path / "x.json"))
    assert r.returncode != 0
    assert "RECUSADO" in (r.stdout + r.stderr)
    assert (logs / "log_analise_total.csv").read_text().startswith("experimento,parcela\nreal")
