"""
Caracterização de sincronizar_nuvem.py — trava o comportamento ATUAL antes de
mexer no arquivo (ver docs/MELHORIAS.md frente #7 / Feathers, "Working
Effectively with Legacy Code": testes de caracterização antes de refatorar).

Não precisa de rclone instalado nem de rede: `subprocess.run` é substituído
por um dublê que só grava os comandos recebidos.

Rodar:  python -m pytest tests/test_characterization_sincronizar.py -q
"""

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
import sincronizar_nuvem as sin


@pytest.fixture(autouse=True)
def _eventos_isolados(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ARQUIVO_EVENTOS", str(tmp_path / "eventos.jsonl"))
    monkeypatch.setattr(config, "ARQUIVO_ULTIMA_SYNC", str(tmp_path / "ultima_sync.txt"))


class ChamadasRegistradas:
    """Dublê de subprocess.run: grava os comandos, não executa nada de verdade."""

    def __init__(self, falha_em=None):
        self.chamadas = []
        self.falha_em = falha_em or set()  # índices que devem levantar CalledProcessError

    def __call__(self, comando, check=True, text=True):
        self.chamadas.append(list(comando))
        if len(self.chamadas) - 1 in self.falha_em:
            raise subprocess.CalledProcessError(returncode=1, cmd=comando)


def test_comando_de_imagens_pinado(tmp_path, monkeypatch):
    monkeypatch.setattr(sin, "PASTA_IMAGENS", "/dados/imagens_analisadas")
    monkeypatch.setattr(sin, "ARQUIVO_CSV", str(tmp_path / "inexistente.csv"))
    monkeypatch.setattr(sin, "NUVEM_DESTINO_IMAGENS", "gdrive:Rover_FAPA_Backups/imagens_analisadas")

    fake = ChamadasRegistradas()
    monkeypatch.setattr(sin.subprocess, "run", fake)

    sin.sincronizar()

    assert len(fake.chamadas) == 1  # CSV não existe -> só roda o comando de imagens
    assert fake.chamadas[0] == [
        "rclone", "copy", "/dados/imagens_analisadas",
        "gdrive:Rover_FAPA_Backups/imagens_analisadas",
        "--update", "--progress", "--transfers=4",
    ]


def test_comando_do_csv_so_roda_se_arquivo_existe(tmp_path, monkeypatch):
    csv_existente = tmp_path / "log_analise_total.csv"
    csv_existente.write_text("cabecalho\n")

    monkeypatch.setattr(sin, "PASTA_IMAGENS", "/dados/imagens_analisadas")
    monkeypatch.setattr(sin, "ARQUIVO_CSV", str(csv_existente))
    monkeypatch.setattr(sin, "NUVEM_DESTINO_IMAGENS", "gdrive:Rover_FAPA_Backups/imagens_analisadas")
    monkeypatch.setattr(sin, "NUVEM_DESTINO_CSV", "gdrive:Rover_FAPA_Backups/relatorios")

    fake = ChamadasRegistradas()
    monkeypatch.setattr(sin.subprocess, "run", fake)

    sin.sincronizar()

    assert len(fake.chamadas) == 2
    assert fake.chamadas[1] == [
        "rclone", "copy", str(csv_existente),
        "gdrive:Rover_FAPA_Backups/relatorios",
        "--update", "--progress",
    ]


def test_falha_no_rclone_sai_com_codigo_1(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sin, "PASTA_IMAGENS", "/dados/imagens_analisadas")
    monkeypatch.setattr(sin, "ARQUIVO_CSV", str(tmp_path / "inexistente.csv"))

    fake = ChamadasRegistradas(falha_em={0})  # a 1ª chamada (imagens) falha
    monkeypatch.setattr(sin.subprocess, "run", fake)

    try:
        sin.sincronizar()
        assert False, "deveria ter levantado SystemExit"
    except SystemExit as exc:
        assert exc.code == 1

    saida = capsys.readouterr().out
    assert "Erro ao sincronizar" in saida


def test_csv_inexistente_nao_interrompe_e_avisa(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sin, "PASTA_IMAGENS", "/dados/imagens_analisadas")
    monkeypatch.setattr(sin, "ARQUIVO_CSV", str(tmp_path / "inexistente.csv"))

    fake = ChamadasRegistradas()
    monkeypatch.setattr(sin.subprocess, "run", fake)

    sin.sincronizar()  # não deve levantar

    saida = capsys.readouterr().out
    assert "ainda não foi criado" in saida
    assert "concluída" in saida
