"""
Smoke test do config.py — o refactor/config não muda comportamento, só
centraliza. Este teste trava o contrato: nomes existem, tipos certos,
caminhos absolutos e sob BASE_DIR.

Rodar:  python -m pytest tests/ -q      (ou)   python tests/test_config.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def test_base_dir_absoluto():
    assert os.path.isabs(config.BASE_DIR)


def test_pastas_sob_base_dir():
    for pasta in config.PASTAS_DE_TRABALHO:
        assert os.path.isabs(pasta)
        assert pasta.startswith(config.BASE_DIR)


def test_arquivos_de_dados_no_logs():
    assert config.ARQUIVO_CSV.startswith(config.PASTA_LOGS)
    assert config.ARQUIVO_STATUS.startswith(config.PASTA_LOGS)
    assert config.ARQUIVO_CSV.endswith(".csv")
    assert config.ARQUIVO_STATUS.endswith(".json")


def test_scripts_do_pipeline_existem():
    for script in (config.SCRIPT_CAPTURADOR, config.SCRIPT_ANALISADOR,
                   config.SCRIPT_SINCRONIZAR):
        assert os.path.isfile(script), script


def test_parametros_numericos():
    assert isinstance(config.INTERVALO_CAPTURA_S, float)
    assert config.INTERVALO_CAPTURA_S > 0
    assert isinstance(config.INTERVALO_VERIFICACAO_S, float)
    assert 0.0 < config.CONFIANCA_IA <= 1.0
    assert 0.0 < config.TAXA_PRECISAO <= 1.0
    assert 0.0 < config.TAXA_RECALL <= 1.0
    assert config.RESOLUCAO_CAPTURA == (1280, 720)
    assert config.CLASSES_IA == [0]


def test_nuvem_derivada_do_remote():
    assert config.NUVEM_DESTINO_IMAGENS.startswith(config.RCLONE_REMOTE + ":")
    assert config.NUVEM_BASE in config.NUVEM_DESTINO_IMAGENS
    assert config.NUVEM_BASE in config.NUVEM_DESTINO_CSV


def test_env_var_override(monkeypatch=None):
    # Sem pytest: pula. Com pytest: valida ROVER_BASE_DIR.
    if monkeypatch is None:
        return
    monkeypatch.setenv("ROVER_INTERVALO_CAPTURA_S", "1.5")
    import importlib
    importlib.reload(config)
    assert config.INTERVALO_CAPTURA_S == 1.5
    monkeypatch.delenv("ROVER_INTERVALO_CAPTURA_S")
    importlib.reload(config)


def test_versao_definida():
    assert isinstance(config.VERSAO, str) and config.VERSAO


if __name__ == "__main__":
    falhas = 0
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok    {nome}")
            except AssertionError as e:
                falhas += 1
                print(f"FALHA {nome}: {e}")
    sys.exit(1 if falhas else 0)
