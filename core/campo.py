"""
core/campo.py: o gêmeo digital do ensaio, como um snapshot só de leitura.

Junta num único JSON versionado o que o sistema já grava:

    planilha da semeadora (Plan1) -> geometria do ensaio e grãos por plot
    CSV canônico (core/registro)  -> contagem de cada foto
    status_analise.json           -> estado do analisador, fila, última foto
    parcela_atual.json            -> onde o operador diz que o rover está
    eventos.jsonl                 -> linha do tempo (captura, sync, export)

Quem desenha (a visão 3D em web/, ou qualquer outro consumidor) só lê isto.
Regras, tiradas do que costuma dar errado em painel 3D "bonito":

1. Dados primeiro: a visão é só mais um jeito de ver o mesmo dado.
2. Um lugar só calcula indicador (aqui). A visão não soma nada, então dois
   blocos da tela nunca discordam.
3. Horário de evento vem do arquivo e nunca é recalculado a partir de
   "agora". "agora" só entra nas idades (`idade_*_s`), e é injetável.
4. Só o medido. Sem odômetro/GPS e sem as caixas do YOLO gravadas, não há
   posição ao longo da carreira nem posição de planta: o snapshot não inventa.

Desempenho: o CSV e o eventos.jsonl só crescem (append). `Cache` lê apenas
o que entrou desde a última vez; quem monta snapshot toda hora (o servidor)
guarda um `Cache`. Sem cache, lê tudo (CLI, testes).

Uso:  python -m core.campo [--experimento NOME] [--compacto] [--sem-telemetria]

Ref.: docs/GEMEO-3D.md.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import shutil
import sys
from bisect import bisect_left, insort
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from statistics import median

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from . import parcela as parcela_mod
from . import status as status_mod

SCHEMA_VERSION = 1
SEM_EXPERIMENTO = "(sem experimento)"

# Colunas da Plan1 além de X/Y/experimento (essas o core/parcela.py já conhece).
_COL_COMPRIMENTO = "Comprimento Parcela (cm)"
_COL_PASSAGEM = "Passagem (cm)"
_COL_GRAOS = "Grãos por Parcela"
_COL_ESPACAMENTO = "Espaçam. fil (cm)"
_COL_CARREIRAS = "Carreiras por parcela"

# Gravidade dos alertas, da menor para a maior.
_GRAVIDADE = {None: 0, "atencao": 1, "critico": 2}

NOTA_CONTAGEM = (
    "Plantas = soma da contagem corrigida de cada foto (precisão/recall fixos "
    "em config.py). Fotos sobrepostas podem contar a mesma planta duas vezes. "
    "A calibração de campo (RV-08) ainda não foi feita."
)

_PROCESSOS = (
    ("painel", "painel_controle.py"),
    ("analisador", "analisador_em_background.py"),
    ("capturador", "capturador.py"),
)


# ---------------------------------------------------------------------------
# fontes
# ---------------------------------------------------------------------------
@dataclass
class Fontes:
    """Caminhos das fontes. Padrão: os de config.py (os que o rover usa)."""
    csv: str
    status: str
    parcela: str
    eventos: str
    planilha: str
    ultima_sync: str

    @classmethod
    def do_config(cls):
        return cls(
            csv=config.ARQUIVO_CSV,
            status=config.ARQUIVO_STATUS,
            parcela=config.ARQUIVO_PARCELA,
            eventos=config.ARQUIVO_EVENTOS,
            planilha=config.PLANILHA_PROGRAMACAO,
            ultima_sync=config.ARQUIVO_ULTIMA_SYNC,
        )

    @property
    def marcador_demo(self):
        """Arquivo `DEMO` ao lado do CSV: os dados são de demonstração."""
        return os.path.join(os.path.dirname(self.csv), "DEMO")

    def assinatura(self):
        """(caminho, mtime, tamanho) de cada fonte. Muda quando algum arquivo
        muda: serve de chave de cache para quem monta snapshot toda hora."""
        return tuple((c, *_stat(c)) for c in (
            self.csv, self.status, self.parcela, self.eventos,
            self.planilha, self.ultima_sync, self.marcador_demo))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _stat(caminho):
    try:
        st = os.stat(caminho)
        return st.st_mtime_ns, st.st_size
    except (OSError, TypeError, ValueError):
        return None, None


def _ts(texto):
    """'2026-10-15 16:20:01[.123456]' -> datetime (None se vazio/inválido)."""
    if not texto:
        return None
    try:
        return datetime.fromisoformat(str(texto).strip())
    except ValueError:
        return None


def _fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _idade(agora, dt):
    return round((agora - dt).total_seconds(), 1) if dt else None


def _num(valor):
    """Número vindo da planilha/CSV (aceita vírgula decimal). None se vazio."""
    if valor is None:
        return None
    texto = str(valor).strip().replace(",", ".")
    if not texto:
        return None
    try:
        return float(texto)
    except ValueError:
        return None


def _pct(valor):
    return f"{valor * 100:.0f}%"


def _ler_json(caminho):
    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
    except (OSError, TypeError, ValueError):
        return {}
    return dados if isinstance(dados, dict) else {}


def _nome_experimento(valor):
    return (valor or "").strip() or SEM_EXPERIMENTO


def _primeiro_depois(instantes, t):
    """Primeiro instante da lista ordenada que é >= t (None se não houver)."""
    if t is None:
        return None
    i = bisect_left(instantes, t)
    return instantes[i] if i < len(instantes) else None


def _pior(itens):
    """(alerta, motivo) mais grave de uma lista de dicts com essas chaves."""
    pior = max(itens, key=lambda i: _GRAVIDADE[i.get("alerta")], default=None)
    if not pior or not pior.get("alerta"):
        return None, None
    return pior["alerta"], pior.get("motivo")


# ---------------------------------------------------------------------------
# leitura incremental (CSV e eventos só crescem)
# ---------------------------------------------------------------------------
class _LeitorIncremental:
    """Lê um arquivo que só cresce, a partir de onde parou. Se o arquivo for
    trocado (outro inode, ex.: CSV antigo arquivado) ou encolher, recomeça do
    zero. Linha incompleta no fim (escrita em andamento) fica para a próxima.
    Limitação: não suporta quebra de linha dentro de um campo."""

    def __init__(self):
        self._caminho = None
        self._ino = None
        self._offset = 0
        self._zerar()

    def _zerar(self):
        raise NotImplementedError

    def _novas_linhas(self, caminho):
        try:
            st = os.stat(caminho)
        except (OSError, TypeError, ValueError):
            if self._offset or self._ino is not None:
                self._zerar()
            self._caminho, self._ino, self._offset = caminho, None, 0
            return []
        if (caminho, st.st_ino) != (self._caminho, self._ino) or st.st_size < self._offset:
            self._zerar()
            self._caminho, self._ino, self._offset = caminho, st.st_ino, 0
        if st.st_size == self._offset:
            return []
        with open(caminho, "rb") as f:
            f.seek(self._offset)
            bloco = f.read(st.st_size - self._offset)
        fim = bloco.rfind(b"\n")
        if fim < 0:
            return []
        self._offset += fim + 1
        return bloco[:fim + 1].decode("utf-8", errors="replace").splitlines()


class _LeitorCSV(_LeitorIncremental):
    """Acumula o CSV canônico por experimento e por (x, y, linha)."""

    def _zerar(self):
        self.cabecalho = None
        self.por_exp = {}          # nome -> {"acc": {...}, "sem_parcela": n, "linhas": n}
        self.total = 0             # linhas com parcela (como registro.ler)
        self.ultimo_experimento = None

    def atualizar(self, caminho):
        linhas = self._novas_linhas(caminho)
        if linhas and self.cabecalho is None:
            self.cabecalho = next(csv.reader([linhas[0]]), [])
            linhas = linhas[1:]
        for valores in csv.reader(linhas):
            d = dict(zip(self.cabecalho, valores))
            if not (d.get("parcela") or "").strip():
                continue
            nome = _nome_experimento(d.get("experimento"))
            exp = self.por_exp.setdefault(nome, {"acc": {}, "sem_parcela": 0, "linhas": 0})
            exp["linhas"] += 1
            self.total += 1
            self.ultimo_experimento = nome
            _somar(exp, d)
        return self


class _LeitorEventos(_LeitorIncremental):
    """Do eventos.jsonl guarda só o que o snapshot usa: os últimos N, os
    instantes de sync/export, se a captura está ligada, quando a carreira
    atual começou e quanto duraram as carreiras feitas com a câmera ligada
    (para estimar a posição do rover, que não tem odômetro)."""

    def _zerar(self):
        self.recentes = deque(maxlen=config.CAMPO_EVENTOS_LIMITE)
        self.syncs, self.exports = [], []
        self.capturando = False
        self.ultimo_ts = None
        self.total = 0
        self.inicio = (None, None)          # (identificador, instante) da carreira atual
        self.duracoes = deque(maxlen=200)   # segundos de cada carreira capturada

    def _fechar_carreira(self, t):
        """Fecha a carreira em andamento (se a câmera estava ligada)."""
        comeco = self.inicio[1]
        if self.capturando and comeco and t:
            d = (t - comeco).total_seconds()
            if 1 <= d <= 1800:              # fora disso: pausa, não é carreira
                self.duracoes.append(d)

    def atualizar(self, caminho):
        for ln in self._novas_linhas(caminho):
            try:
                ev = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if not isinstance(ev, dict):
                continue
            self.total += 1
            self.recentes.append(ev)
            t, nome = _ts(ev.get("ts")), ev.get("evento")
            if t:
                self.ultimo_ts = t
                if nome == "sync_ok":
                    insort(self.syncs, t)
                elif nome == "planilha_exportada":
                    insort(self.exports, t)
            # vale o último evento que decide se a captura está ligada
            if nome == "captura_iniciada":
                self.capturando = True
                self.inicio = (ev.get("parcela"), t)
            elif nome == "parcela_avancada":
                self._fechar_carreira(t)
                self.inicio = (ev.get("para"), t)
            elif nome == "parcela_voltou":
                self.inicio = (ev.get("para"), t)
            elif nome == "captura_parada":
                self._fechar_carreira(t)
                self.capturando = False
            elif nome == "painel_iniciado":
                self.capturando = False
                self.inicio = (ev.get("parcela"), t)
        return self


class Cache:
    """Estado guardado entre snapshots: o servidor mantém um; CLI e testes
    usam um novo a cada chamada. Não é thread-safe (o servidor usa lock)."""

    def __init__(self):
        self.csv = _LeitorCSV()
        self.eventos = _LeitorEventos()
        self._planilha_chave = None
        self._planilha = (None, None)

    def planilha(self, caminho):
        """(programação para geometria/grãos, lista do navegador), relidas só
        quando o arquivo muda (abrir .xlsx é lento)."""
        chave = (caminho, *_stat(caminho))
        if chave != self._planilha_chave:
            self._planilha_chave = chave
            self._planilha = (_ler_programacao(caminho), parcela_mod.carregar_plots(caminho))
        return self._planilha


# ---------------------------------------------------------------------------
# planilha e geometria
# ---------------------------------------------------------------------------
def _ler_programacao(caminho):
    """Plan1 -> ([plot, ...], experimento) na ordem do arquivo, ou None.
    Cada plot traz X, Y, grãos e as medidas que a planilha tiver."""
    linhas = parcela_mod.ler_planilha(caminho)
    if not linhas:
        return None
    plots, vistos, experimento = [], set(), ""
    for d in linhas:
        x, y = _num(d.get(parcela_mod._COL_X)), _num(d.get(parcela_mod._COL_Y))
        if x is None or y is None or (int(x), int(y)) in vistos:
            continue
        vistos.add((int(x), int(y)))
        plots.append({
            "x": int(x), "y": int(y),
            "graos": _num(d.get(_COL_GRAOS)),
            "comprimento_cm": _num(d.get(_COL_COMPRIMENTO)),
            "passagem_cm": _num(d.get(_COL_PASSAGEM)),
            "espacamento_cm": _num(d.get(_COL_ESPACAMENTO)),
            "carreiras": _num(d.get(_COL_CARREIRAS)),
        })
        if not experimento and d.get(parcela_mod._COL_EXP):
            experimento = str(d[parcela_mod._COL_EXP]).strip()
    return (plots, experimento) if plots else None


def _parametros(plots_planilha):
    """Medidas do ensaio: da planilha (primeira linha que tiver) ou de config."""
    def primeiro(campo, padrao):
        for p in plots_planilha:
            if p.get(campo):
                return p[campo]
        return padrao

    carreiras = int(primeiro("carreiras", config.PARCELA_LINHAS))
    espacamento = primeiro("espacamento_cm", config.CAMPO_ESPACAMENTO_CM) / 100
    return {
        "carreiras_por_plot": carreiras,
        "espacamento_m": round(espacamento, 3),
        "largura_plot_m": round(carreiras * espacamento, 3),
        "comprimento_plot_m": round(primeiro("comprimento_cm", config.CAMPO_COMPRIMENTO_CM) / 100, 3),
        "passagem_m": round(primeiro("passagem_cm", config.CAMPO_PASSAGEM_CM) / 100, 3),
        "folga_m": round(config.CAMPO_FOLGA_CM / 100, 3),
        "eixos_trocados": config.CAMPO_TROCAR_EIXOS,
    }


def _origem(x, y, par):
    """Canto do plot no plano do campo, em metros: u = transversal às
    carreiras, v = ao longo delas. Padrão: X anda em u e Y em v."""
    iu, iv = (y, x) if par["eixos_trocados"] else (x, y)
    u = (iu - 1) * (par["largura_plot_m"] + par["folga_m"])
    v = (iv - 1) * (par["comprimento_plot_m"] + par["passagem_m"])
    return [round(u, 3), round(v, 3)]


# ---------------------------------------------------------------------------
# CSV: soma por carreira
# ---------------------------------------------------------------------------
def _chave(linha_csv):
    """(x, y, linha) de uma linha do CSV: colunas decompostas, senão o
    identificador. None se for nome antigo (fora do formato estruturado)."""
    x, y, l = (_num(linha_csv.get(c)) for c in ("X", "Y", "linha"))
    if None not in (x, y, l):
        return int(x), int(y), int(l)
    return parcela_mod.parse_identificador((linha_csv.get("parcela") or "").strip())


def _somar(exp, d):
    """Soma uma linha do CSV no acumulado do experimento."""
    chave = _chave(d)
    if chave is None:
        exp["sem_parcela"] += 1
        return
    a = exp["acc"].setdefault(chave, {
        "plantulas": 0, "plantulas_bruto": 0, "imagens": 0,
        "primeira": None, "ultima": None, "ultima_analise": None,
        "versoes_modelo": set(), "versoes_software": set(),
    })
    a["plantulas"] += int(_num(d.get("plantulas_corrigido")) or 0)
    a["plantulas_bruto"] += int(_num(d.get("plantulas_bruto")) or 0)
    a["imagens"] += 1
    t_img, t_an = _ts(d.get("timestamp_imagem")), _ts(d.get("timestamp_analise"))
    if t_img:
        a["primeira"] = min(t for t in (a["primeira"], t_img) if t)
        a["ultima"] = max(t for t in (a["ultima"], t_img) if t)
    if t_an:
        a["ultima_analise"] = max(t for t in (a["ultima_analise"], t_an) if t)
    if d.get("versao_modelo"):
        a["versoes_modelo"].add(d["versao_modelo"])
    if d.get("versao_software"):
        a["versoes_software"].add(d["versao_software"])


# ---------------------------------------------------------------------------
# alertas (cor só em exceção: docs/MELHORIAS.md frente #6)
# ---------------------------------------------------------------------------
def _alerta_carreira(plantulas, emergencia):
    """(alerta, motivo) de uma carreira já analisada."""
    if plantulas == 0:
        return "critico", "nenhuma planta contada"
    if emergencia is None:
        return None, None
    if emergencia < config.CAMPO_EMERGENCIA_CRITICO:
        return "critico", (f"emergência {_pct(emergencia)} "
                           f"(abaixo de {_pct(config.CAMPO_EMERGENCIA_CRITICO)})")
    if emergencia < config.CAMPO_EMERGENCIA_ATENCAO:
        return "atencao", (f"emergência {_pct(emergencia)} "
                           f"(abaixo de {_pct(config.CAMPO_EMERGENCIA_ATENCAO)})")
    if emergencia > config.CAMPO_EMERGENCIA_MAXIMA:
        return "atencao", (f"emergência {_pct(emergencia)}: acima do semeado, "
                           f"conferir sobreposição das fotos")
    return None, None


# ---------------------------------------------------------------------------
# blocos do snapshot
# ---------------------------------------------------------------------------
def _carreira(x, y, l, origem, par, esperado, a, syncs, exports):
    c = {
        "linha": l,
        "id": parcela_mod.identificador(x, y, l),
        "centro_u_m": round(origem[0] + (l - 0.5) * par["espacamento_m"], 3),
        "esperado": round(esperado, 1) if esperado else None,
        "estado": "pendente", "alerta": None, "motivo": None,
        "plantulas": None, "plantulas_bruto": None, "emergencia": None,
        "imagens": 0,
        "primeira_imagem": None, "ultima_imagem": None, "ultima_analise": None,
        "sincronizada_em": None, "exportada_em": None,
        "versoes_modelo": [], "versoes_software": [],
        "incerteza": None,   # RV-08: entra quando houver curva de calibração
    }
    if not a:
        return c
    emergencia = a["plantulas"] / esperado if esperado else None
    c.update({
        "estado": "analisada",
        "plantulas": a["plantulas"],
        "plantulas_bruto": a["plantulas_bruto"],
        "emergencia": round(emergencia, 3) if emergencia is not None else None,
        "imagens": a["imagens"],
        "primeira_imagem": _fmt(a["primeira"]),
        "ultima_imagem": _fmt(a["ultima"]),
        "ultima_analise": _fmt(a["ultima_analise"]),
        "sincronizada_em": _fmt(_primeiro_depois(syncs, a["ultima_analise"])),
        "exportada_em": _fmt(_primeiro_depois(exports, a["ultima_analise"])),
        "versoes_modelo": sorted(a["versoes_modelo"]),
        "versoes_software": sorted(a["versoes_software"]),
    })
    c["alerta"], c["motivo"] = _alerta_carreira(a["plantulas"], emergencia)
    return c


def _plot(ordem, p, par, acc, posicao_rover, capturando, syncs, exports):
    x, y, graos = p["x"], p["y"], p.get("graos")
    origem = _origem(x, y, par)
    esperado_carreira = graos / par["carreiras_por_plot"] if graos else None

    carreiras = []
    for l in range(1, par["carreiras_por_plot"] + 1):
        c = _carreira(x, y, l, origem, par, esperado_carreira, acc.get((x, y, l)), syncs, exports)
        if capturando and posicao_rover == (x, y, l):
            # carreira em andamento: contagem parcial, o alerta ainda não vale
            c.update({"estado": "capturando", "alerta": None, "motivo": None})
        carreiras.append(c)

    feitas = [c for c in carreiras if c["estado"] == "analisada"]
    plantulas = sum(c["plantulas"] for c in feitas) if feitas else None
    esperado = esperado_carreira * len(feitas) if (feitas and esperado_carreira) else None
    emergencia = plantulas / esperado if esperado else None
    if not feitas:
        estado = "pendente"
    elif len(feitas) < len(carreiras):
        estado = "parcial"
    else:
        estado = "concluido"
    alerta, motivo = _pior(carreiras)
    return {
        "id": parcela_mod.plot_id(x, y), "x": x, "y": y, "ordem": ordem,
        "origem_m": origem,
        "graos": graos,
        "esperado": round(esperado, 1) if esperado else None,
        "plantulas": plantulas,
        "emergencia": round(emergencia, 3) if emergencia is not None else None,
        "estado": estado, "alerta": alerta, "motivo": motivo,
        "fora_da_planilha": bool(p.get("fora_da_planilha")),
        "carreiras": carreiras,
    }


def _kpis(plots, st, ultima_sync, ultima_atividade, agora):
    # Totais só de carreiras fechadas ("analisada"), para baterem com a soma
    # dos plots. A carreira em captura (parcial) aparece à parte.
    carreiras = [c for p in plots for c in p["carreiras"]]
    analisadas = [c for c in carreiras if c["estado"] == "analisada"]
    em_captura = [c for c in carreiras if c["estado"] == "capturando" and c["plantulas"] is not None]
    com_graos = [c for c in analisadas if c["esperado"]]
    plantulas_com_graos = sum(c["plantulas"] for c in com_graos)
    esperado = sum(c["esperado"] for c in com_graos)
    return {
        "plots_total": len(plots),
        "plots_concluidos": sum(p["estado"] == "concluido" for p in plots),
        "plots_parciais": sum(p["estado"] == "parcial" for p in plots),
        "plots_em_alerta": sum(p["alerta"] is not None for p in plots),
        "carreiras_total": len(carreiras),
        "carreiras_analisadas": len(analisadas),
        "carreiras_em_alerta": sum(c["alerta"] is not None for c in carreiras),
        "progresso": round(len(analisadas) / len(carreiras), 4) if carreiras else None,
        "plantulas": sum(c["plantulas"] for c in analisadas),
        "plantulas_bruto": sum(c["plantulas_bruto"] for c in analisadas),
        "plantulas_em_captura": sum(c["plantulas"] for c in em_captura) if em_captura else None,
        "imagens": sum(c["imagens"] for c in carreiras),
        "esperado": round(esperado, 1) if com_graos else None,
        "emergencia_media": round(plantulas_com_graos / esperado, 3) if esperado else None,
        "fila_pendente": st.fila_pendente if st else None,
        "ultima_sync": _fmt(ultima_sync),
        "idade_sync_s": _idade(agora, ultima_sync),
        "ultima_atividade": _fmt(ultima_atividade),
        "idade_atividade_s": _idade(agora, ultima_atividade),
    }


def _movimento(nav, ev, acc, agora):
    """Onde o rover deve estar ao longo da carreira: ESTIMATIVA, porque não há
    odômetro nem GPS. Tempo desde que a carreira começou (evento gravado pelo
    painel) dividido pela duração típica de uma carreira (mediana do histórico
    de eventos; sem histórico, nº típico de fotos x intervalo; sem nada, padrão)."""
    atual = nav.identificador()
    comeco = ev.inicio[1] if ev.inicio[0] == atual else None
    if len(ev.duracoes) >= 3:
        duracao, fonte = median(ev.duracoes), "histórico de carreiras"
    else:
        fotos = [a["imagens"] for (x, y, l), a in acc.items() if (x, y, l) != (nav.x, nav.y, nav.linha)]
        if len(fotos) >= 3:
            duracao, fonte = median(fotos) * config.INTERVALO_CAPTURA_S, "fotos por carreira"
        else:
            duracao, fonte = config.CAMPO_DURACAO_CARREIRA_PADRAO_S, "padrão (sem histórico)"
    idade = _idade(agora, comeco)
    progresso = None
    if ev.capturando and idade is not None and duracao > 0:
        progresso = round(min(1.0, max(0.0, idade / duracao)), 3)
    serpentina = config.CAMPO_TRAJETO == "serpentina"
    return {
        "inicio_carreira": _fmt(comeco),
        "idade_carreira_s": idade,
        "duracao_tipica_s": round(duracao, 1),
        "fonte_duracao": fonte,
        "progresso_estimado": progresso,
        "sentido": -1 if (serpentina and nav.linha % 2 == 0) else 1,
        "trajeto": config.CAMPO_TRAJETO,
        "intervalo_captura_s": config.INTERVALO_CAPTURA_S,
    }


def _rover(st, nav, capturando, agora, movimento=None):
    status_em = _ts(st.timestamp) if st else None
    idade = _idade(agora, status_em)
    teve_foto = bool(st and st.ultima_imagem)
    rover = {
        "posicao": None,
        "movimento": None,
        "capturando": capturando,
        "analisador_estado": st.analisador_estado if st else "desconhecido",
        "fila_pendente": st.fila_pendente if st else None,
        "ultima_imagem": st.ultima_imagem if teve_foto else None,
        "ultima_parcela_analisada": (st.parcela or None) if st else None,
        "plantulas_ultima": st.plantulas_corrigido if teve_foto else None,
        "plantulas_ultima_bruto": st.plantulas_bruto if teve_foto else None,
        "status_em": _fmt(status_em),
        "idade_status_s": idade,
    }
    if nav is not None:
        rover["posicao"] = {
            "parcela": nav.identificador(),
            "plot": parcela_mod.plot_id(nav.x, nav.y),
            "x": nav.x, "y": nav.y, "linha": nav.linha,
            "modo": nav.modo,
            "ordem": nav.indice + 1 if nav.plots else None,
            "total_plots": nav.total_plots,
        }
        rover["movimento"] = movimento

    alertas = []
    if st and st.analisador_estado == "erro":
        alertas.append({"alerta": "critico", "codigo": "analisador_erro", "motivo": "analisador em erro"})
    if capturando and idade is not None and idade > config.CAMPO_STATUS_VELHO_S:
        alertas.append({"alerta": "atencao", "codigo": "analise_parada",
                        "motivo": f"captura ligada e nenhuma análise há {idade:.0f} s"})
    if st and st.fila_pendente >= config.CAMPO_FILA_ATENCAO:
        alertas.append({"alerta": "atencao", "codigo": "fila",
                        "motivo": f"fila de análise com {st.fila_pendente} fotos"})
    rover["alertas"] = alertas
    rover["alerta"], rover["motivo"] = _pior(alertas)
    return rover


def _saude(tele, kpis):
    alertas = []
    livre = (tele or {}).get("disco_livre_gb")
    if livre is not None:
        if livre < config.CAMPO_DISCO_CRITICO_GB:
            alertas.append({"alerta": "critico", "codigo": "disco", "motivo": f"disco com {livre:.1f} GB livres"})
        elif livre < config.CAMPO_DISCO_ATENCAO_GB:
            alertas.append({"alerta": "atencao", "codigo": "disco", "motivo": f"disco com {livre:.1f} GB livres"})
    if kpis["imagens"]:
        idade = kpis["idade_sync_s"]
        if idade is None:
            alertas.append({"alerta": "atencao", "codigo": "backup", "motivo": "nenhum backup na nuvem ainda"})
        elif idade > config.CAMPO_SYNC_VELHA_S:
            alertas.append({"alerta": "atencao", "codigo": "backup",
                            "motivo": f"último backup há {idade / 3600:.1f} h"})
    alerta, motivo = _pior(alertas)
    return {"telemetria": tele, "alertas": alertas, "alerta": alerta, "motivo": motivo}


def _limiares():
    return {
        "emergencia_atencao": config.CAMPO_EMERGENCIA_ATENCAO,
        "emergencia_critico": config.CAMPO_EMERGENCIA_CRITICO,
        "emergencia_maxima": config.CAMPO_EMERGENCIA_MAXIMA,
        "fila_atencao": config.CAMPO_FILA_ATENCAO,
        "status_velho_s": config.CAMPO_STATUS_VELHO_S,
        "sync_velha_s": config.CAMPO_SYNC_VELHA_S,
        "disco_atencao_gb": config.CAMPO_DISCO_ATENCAO_GB,
        "disco_critico_gb": config.CAMPO_DISCO_CRITICO_GB,
    }


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def montar_snapshot(experimento=None, fontes=None, agora=None, telemetria=None, cache=None):
    """Monta o snapshot do ensaio (dict pronto para json.dumps).

    `experimento`: qual mostrar (padrão: o da campanha atual do painel).
    `fontes`: caminhos (padrão: config.py). `agora`: relógio (para idades).
    `telemetria`: dict de `telemetria()` ou None (testes, fora do Pi).
    `cache`: um `Cache` reaproveitado entre chamadas (só lê o que é novo).
    """
    fontes = fontes or Fontes.do_config()
    agora = agora or datetime.now()
    cache = cache or Cache()

    # --- 1. fontes (cada uma tolera arquivo ausente) ---
    leitor_csv = cache.csv.atualizar(fontes.csv)
    ev = cache.eventos.atualizar(fontes.eventos)
    st = status_mod.ler(fontes.status)
    programacao, plots_navegador = cache.planilha(fontes.planilha)
    plots_planilha, exp_planilha = programacao if programacao else ([], "")
    exp_atual = (_ler_json(fontes.parcela).get("experimento") or "").strip() or exp_planilha

    # --- 2. qual experimento ---
    experimentos = sorted(set(leitor_csv.por_exp) | {e for e in (exp_atual, exp_planilha) if e})
    escolhido = (experimento or exp_atual or leitor_csv.ultimo_experimento
                 or config.EXPERIMENTO_PADRAO)
    campanha_atual = bool(exp_atual) and escolhido == exp_atual
    usa_planilha = bool(plots_planilha) and (campanha_atual or escolhido == exp_planilha)

    # --- 3. a grade de plots ---
    if usa_planilha:
        lista = [dict(p) for p in plots_planilha]
    elif campanha_atual:
        # sem planilha: a grade que o operador navega no modo manual
        lista = [{"x": x, "y": y, "graos": None}
                 for x in range(config.PARCELA_X_MIN, config.PARCELA_X_MAX + 1)
                 for y in range(config.PARCELA_Y_MIN, config.PARCELA_Y_MAX + 1)]
    else:
        lista = []   # experimento antigo: só o que aparece no CSV
    grade_definida = bool(lista)

    dados_exp = leitor_csv.por_exp.get(escolhido, {"acc": {}, "sem_parcela": 0, "linhas": 0})
    acc = dados_exp["acc"]
    conhecidos = {(p["x"], p["y"]) for p in lista}
    for x, y in sorted({(x, y) for (x, y, _) in acc} - conhecidos):
        lista.append({"x": x, "y": y, "graos": None, "fora_da_planilha": grade_definida})

    par = _parametros(plots_planilha if usa_planilha else [])
    fora_da_grade = sum(a["imagens"] for (_, _, l), a in acc.items()
                        if not 1 <= l <= par["carreiras_por_plot"])

    # --- 4. rover: posição só na campanha atual, e só se o painel já gravou ---
    nav = None
    if campanha_atual and os.path.exists(fontes.parcela):
        nav = parcela_mod.Navegador(
            plots=plots_navegador[0] if plots_navegador else None,
            experimento=exp_atual,
        ).restaurar(fontes.parcela)
    posicao_rover = (nav.x, nav.y, nav.linha) if nav else None

    # --- 5. última sync: arquivo do sincronizar_nuvem.py, senão o evento ---
    ultima_sync = None
    try:
        with open(fontes.ultima_sync, encoding="utf-8") as f:
            ultima_sync = _ts(f.read())
    except (OSError, TypeError, ValueError):
        pass
    ultima_sync = ultima_sync or (ev.syncs[-1] if ev.syncs else None)

    plots = [_plot(i, p, par, acc, posicao_rover, ev.capturando, ev.syncs, ev.exports)
             for i, p in enumerate(lista, start=1)]

    marcas = [ev.ultimo_ts] + [a["ultima_analise"] for a in acc.values()]
    marcas = [t for t in marcas if t]
    ultima_atividade = max(marcas) if marcas else None

    kpis = _kpis(plots, st, ultima_sync, ultima_atividade, agora)
    # Demonstração: o "rover" é simulado e esta máquina não é o Pi. A
    # telemetria dela (disco do /tmp, processos do painel parados) contradiria
    # o rover sintético, então nem entra.
    demo = os.path.exists(fontes.marcador_demo)
    if demo:
        telemetria = None
    largura = max((p["origem_m"][0] + par["largura_plot_m"] for p in plots), default=0.0)
    comprimento = max((p["origem_m"][1] + par["comprimento_plot_m"] for p in plots), default=0.0)

    return {
        "schema": SCHEMA_VERSION,
        "gerado_em": _fmt(agora),
        "versao_software": config.VERSAO,
        "demo": demo,
        "experimento": escolhido,
        "experimentos": experimentos,
        "campanha_atual": campanha_atual,
        "fontes": {
            "planilha": os.path.basename(fontes.planilha) if usa_planilha else None,
            "csv_total": leitor_csv.total,
            "csv_linhas": dados_exp["linhas"],
            "csv_sem_parcela": dados_exp["sem_parcela"],
            "csv_fora_da_grade": fora_da_grade,
            "status": st is not None,
            "eventos": ev.total,
        },
        "nota_contagem": NOTA_CONTAGEM,
        "limiares": _limiares(),
        "campo": {
            **par,
            "largura_m": round(largura, 3),
            "comprimento_m": round(comprimento, 3),
            "geo": {
                "lat": config.CAMPO_GEO_LAT,
                "lon": config.CAMPO_GEO_LON,
                "rumo_graus": config.CAMPO_GEO_RUMO_GRAUS,
                "espelhar": config.CAMPO_GEO_ESPELHAR,
                "aproximado": config.CAMPO_GEO_APROXIMADO,
                "fuso_horas": config.CAMPO_FUSO_HORAS,
            },
            "plots": plots,
        },
        "rover": _rover(st, nav, ev.capturando, agora,
                        _movimento(nav, ev, acc, agora) if nav else None),
        "kpis": kpis,
        "saude": _saude(telemetria, kpis),
        "eventos": list(ev.recentes),
    }


# ---------------------------------------------------------------------------
# telemetria do Pi (só leitura, tudo opcional)
# ---------------------------------------------------------------------------
def _temperatura_cpu():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", encoding="ascii") as f:
            return round(int(f.read().strip()) / 1000, 1)
    except (OSError, ValueError):
        return None


def _disco_livre_gb():
    try:
        return round(shutil.disk_usage(config.BASE_DIR).free / 1e9, 1)
    except OSError:
        return None


def _processo_vivo(script):
    """True/False olhando /proc (Linux); None se não der para saber."""
    if not os.path.isdir("/proc"):
        return None
    alvo = script.encode()
    for caminho in glob.glob("/proc/[0-9]*/cmdline"):
        try:
            with open(caminho, "rb") as f:
                partes = f.read().split(b"\0")
        except OSError:
            continue
        if any(os.path.basename(p) == alvo for p in partes):
            return True
    return False


def telemetria():
    """Saúde do Pi: temperatura, disco livre e quais processos estão vivos.
    O que não der para ler (ex.: fora do Pi) vem None, nunca levanta."""
    return {
        "cpu_temp_c": _temperatura_cpu(),
        "disco_livre_gb": _disco_livre_gb(),
        "processos": {nome: _processo_vivo(script) for nome, script in _PROCESSOS},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Snapshot do ensaio (gêmeo digital) em JSON.")
    ap.add_argument("--experimento", help="experimento a montar (padrão: o atual do painel)")
    ap.add_argument("--compacto", action="store_true", help="JSON numa linha só")
    ap.add_argument("--sem-telemetria", action="store_true",
                    help="não lê temperatura/disco/processos")
    args = ap.parse_args(argv)
    snap = montar_snapshot(experimento=args.experimento,
                           telemetria=None if args.sem_telemetria else telemetria())
    json.dump(snap, sys.stdout, ensure_ascii=False, indent=None if args.compacto else 2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
