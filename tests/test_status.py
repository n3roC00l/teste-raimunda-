"""
Testes do schema único de status (core/status.py) e da regra de acumulado
que conserta o "TOTAL ACUMULADO" travado em 0.

Rodar:  python -m pytest tests/ -q     (ou)    python tests/test_status.py
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import status as s


def _tmp():
    d = tempfile.mkdtemp()
    return os.path.join(d, "status_analise.json")


def test_ler_inexistente_retorna_none():
    assert s.ler(_tmp()) is None


def test_round_trip():
    p = _tmp()
    st = s.StatusAnalise(parcela="trat_A_linha_1", plantulas_bruto=10,
                         plantulas_corrigido=11, total_parcela_corrigido=11)
    s.escrever(p, st)
    back = s.ler(p)
    assert back.parcela == "trat_A_linha_1"
    assert back.plantulas_corrigido == 11
    assert back.total_parcela_corrigido == 11
    assert back.schema == s.SCHEMA_VERSION
    assert back.timestamp  # foi carimbado


def test_arquivo_pre_schema_v20_retorna_none():
    # Formato v2.0: sem a chave "schema". Não dá para confiar nos totais.
    p = _tmp()
    with open(p, "w") as f:
        json.dump({"ultima_imagem_analisada": "x.jpg",
                   "plantulas_detectadas_ia": 5}, f)
    assert s.ler(p) is None


def test_schema_futuro_retorna_none():
    p = _tmp()
    with open(p, "w") as f:
        json.dump({"schema": s.SCHEMA_VERSION + 1, "parcela": "z"}, f)
    assert s.ler(p) is None


def test_json_corrompido_retorna_none():
    p = _tmp()
    with open(p, "w") as f:
        f.write("{lixo parcial")
    assert s.ler(p) is None


def test_escrita_atomica_nao_deixa_orfaos():
    p = _tmp()
    d = os.path.dirname(p)
    for _ in range(3):
        s.escrever(p, s.StatusAnalise(parcela="A"))
    orfaos = [x for x in os.listdir(d) if x.startswith(".status_")]
    assert not orfaos, orfaos


def test_from_dict_ignora_chaves_desconhecidas():
    st = s.StatusAnalise.from_dict({"schema": 1, "parcela": "A", "campo_novo": 42})
    assert st.parcela == "A"
    assert not hasattr(st, "campo_novo")


# --- regra de acumulado (a que conserta o bug do TOTAL) --------------------

def _acumular(estado, setor, bruto, corrigido):
    """Réplica da regra em analisador_em_background.analisar_imagem."""
    if setor != estado.parcela:
        estado.parcela = setor
        estado.total_parcela_bruto = 0
        estado.total_parcela_corrigido = 0
    estado.total_parcela_bruto += bruto
    estado.total_parcela_corrigido += corrigido
    estado.plantulas_bruto = bruto
    estado.plantulas_corrigido = corrigido


def test_acumulado_soma_dentro_da_parcela():
    e = s.StatusAnalise()
    _acumular(e, "trat_A_linha_1", 10, 11)
    _acumular(e, "trat_A_linha_1", 8, 9)
    _acumular(e, "trat_A_linha_1", 12, 13)
    assert e.total_parcela_bruto == 30
    assert e.total_parcela_corrigido == 33     # <-- antes ficava travado em 0
    assert e.plantulas_corrigido == 13         # última foto


def test_acumulado_zera_ao_trocar_de_parcela():
    e = s.StatusAnalise()
    _acumular(e, "trat_A_linha_1", 10, 11)
    _acumular(e, "trat_A_linha_1", 10, 11)
    assert e.total_parcela_corrigido == 22
    _acumular(e, "trat_B_linha_2", 5, 6)
    assert e.parcela == "trat_B_linha_2"
    assert e.total_parcela_corrigido == 6


def test_acumulado_sobrevive_a_reinicio():
    p = _tmp()
    e = s.StatusAnalise()
    _acumular(e, "trat_A_linha_1", 10, 11)
    _acumular(e, "trat_A_linha_1", 10, 11)
    s.escrever(p, e)

    # "reinício": novo processo lê o status e retoma
    e2 = s.StatusAnalise()
    anterior = s.ler(p)
    assert anterior is not None
    e2.parcela = anterior.parcela
    e2.total_parcela_bruto = anterior.total_parcela_bruto
    e2.total_parcela_corrigido = anterior.total_parcela_corrigido

    _acumular(e2, "trat_A_linha_1", 4, 5)
    assert e2.total_parcela_corrigido == 27


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
