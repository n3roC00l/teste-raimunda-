"""
ferramentas/demo_campanha.py: campanha SINTÉTICA para demonstrar e testar a visão 3D.

Grava, numa pasta à parte, os mesmos arquivos que o rover grava (planilha,
CSV canônico, status, posição do painel, eventos), com contagens INVENTADAS
e o marcador DEMO: o snapshot sai com "demo": true e a tela mostra a faixa
"DEMONSTRAÇÃO". Recusa gravar numa pasta que já tenha dados sem o marcador.

    # snapshot estático para o modo ?demo do web/ (data fixa, reprodutível)
    python ferramentas/demo_campanha.py --snapshot web/public/demo/snapshot.json

    # campanha "ao vivo": uma foto a cada 0,9 s; em outro terminal:
    #   ROVER_BASE_DIR=/tmp/rover-demo python servidor_visao.py
    python ferramentas/demo_campanha.py --dir /tmp/rover-demo --ao-vivo

A planilha é genérica (12 x 18 plots, 4 densidades sorteadas), não a do ensaio
real. O "campo verdadeiro" tem uma mancha de emergência baixa, uma carreira
zerada (câmera tapada) e uma com dupla contagem, para os alertas aparecerem.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
import tempfile
import time
from datetime import datetime, timedelta

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPERIMENTO = "Ensaio DEMO (dados sintéticos)"
NX, NY, CARREIRAS = 12, 18, 3
DENSIDADES = (240, 270, 300, 330)          # grãos por plot (4 tratamentos)
INICIO_FIXO = datetime(2026, 10, 15, 8, 0, 0)


def _preparar_pasta(pasta):
    """Cria a pasta e o marcador DEMO. Recusa pasta com dados reais."""
    logs = os.path.join(pasta, "logs_analise")
    csv_ = os.path.join(logs, "log_analise_total.csv")
    if os.path.exists(csv_) and not os.path.exists(os.path.join(logs, "DEMO")):
        sys.exit(f"RECUSADO: {logs} tem dados e não tem o marcador DEMO. "
                 "Isto parece a pasta real do rover; use outra pasta.")
    os.makedirs(logs, exist_ok=True)
    for nome in os.listdir(logs):     # recomeça a demo do zero
        os.remove(os.path.join(logs, nome))
    open(os.path.join(logs, "DEMO"), "w").close()
    return logs


def _escrever_planilha(caminho, rng):
    """Plan1 genérica, na ordem da planilha real: X por coluna, Y andando."""
    densidade = {}
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Parcela Compr.(Y)", "Parcela Larg. (X)", "ID Opcional",
                    "Comprimento Parcela (cm)", "Passagem (cm)", "Grãos por Parcela",
                    "Espaçam. fil (cm)", "Carreiras por parcela", "Numero ranhuras",
                    "linha 1", "linha 2", "linha 3"])
        for x in range(1, NX + 1):
            for y in range(1, NY + 1):
                densidade[(x, y)] = rng.choice(DENSIDADES)
                w.writerow([y, x, EXPERIMENTO, 600, 100, densidade[(x, y)], 50,
                            CARREIRAS, 18, "", "", ""])
    return densidade


def _emergencia_verdadeira(x, y, linha, rng):
    """O 'campo verdadeiro' da demo: suave, com ruído e três anomalias."""
    if (x, y, linha) == (4, 12, 2):
        return 0.0                                   # câmera tapada
    if (x, y, linha) == (2, 15, 3):
        return 1.32                                  # dupla contagem
    e = 0.84 + 0.06 * math.sin(x / 2.2) + 0.05 * math.cos(y / 3.1) + rng.gauss(0, 0.035)
    if 3 <= x <= 4 and 5 <= y <= 7:
        e -= 0.33                                    # mancha de emergência baixa
    return max(0.05, min(1.15, e))


class Campanha:
    """Anda pelas carreiras na ordem da planilha, gravando como o rover grava."""

    def __init__(self, pasta, rng, ao_vivo, fotos_por_carreira, manobra_s=3.0, inicio=INICIO_FIXO):
        os.environ["ROVER_BASE_DIR"] = pasta      # antes de importar config
        sys.path.insert(0, RAIZ)
        import config
        from core import io_atomico, registro, status
        self.config, self.io, self.registro, self.status = config, io_atomico, registro, status

        self.rng, self.ao_vivo, self.k = rng, ao_vivo, fotos_por_carreira
        self.manobra_s = manobra_s
        self.sync_a_cada = 12 if ao_vivo else 45     # ao vivo: backup a cada ~2 min
        self.logs = _preparar_pasta(pasta)
        self.densidade = _escrever_planilha(os.path.join(pasta, "programacao_semeadora.csv"), rng)
        registro.garantir_csv(config.ARQUIVO_CSV)
        self.ordem = [(x, y, l) for x in range(1, NX + 1)
                      for y in range(1, NY + 1) for l in range(1, CARREIRAS + 1)]
        self.relogio = inicio
        self.tempo_real = False    # o histórico inicial anda em tempo simulado
        self.i = 0                 # índice da carreira atual em self.ordem
        self.fotos_na_carreira = 0
        self.plano = {}            # (x, y, l) -> contagens corrigidas por foto
        self.st = status.StatusAnalise(experimento=EXPERIMENTO, analisador_estado="pronto")

    # --- gravação no formato do rover -------------------------------------------
    def _agora(self, passo_s):
        if self.tempo_real:
            self.relogio = datetime.now()
        else:
            self.relogio += timedelta(seconds=passo_s)
        return self.relogio

    def _evento(self, nome, **dados):
        linha = {"ts": self.relogio.strftime("%Y-%m-%d %H:%M:%S"), "evento": nome, **dados}
        with open(self.config.ARQUIVO_EVENTOS, "a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")

    def _posicao(self):
        x, y, l = self.ordem[min(self.i, len(self.ordem) - 1)]
        ident = f"X{x}Y{y}L{l}"
        self.io.escrever_json(self.config.ARQUIVO_PARCELA, {
            "experimento": EXPERIMENTO, "modo": "campanha",
            "indice": (x - 1) * NY + (y - 1), "linha": l, "x": x, "y": y,
            "salvo_em": self.relogio.strftime("%Y-%m-%d %H:%M:%S"),
        })
        self.io.escrever_texto(self.config.ARQUIVO_SETOR, ident)
        return ident

    def _gravar_status(self):
        self.st.fila_pendente = self.rng.choice((0, 0, 0, 1, 2)) if self.tempo_real else 0
        self.st.timestamp = self.relogio.strftime("%Y-%m-%d %H:%M:%S")
        self.io.escrever_json(self.config.ARQUIVO_STATUS, self.st.to_dict())

    def _contagens(self, chave):
        """Divide a contagem 'verdadeira' da carreira entre as k fotos."""
        if chave not in self.plano:
            x, y, l = chave
            alvo = round(self.densidade[(x, y)] / CARREIRAS * _emergencia_verdadeira(x, y, l, self.rng))
            cortes = sorted(self.rng.randint(0, alvo) for _ in range(self.k - 1))
            self.plano[chave] = [b - a for a, b in zip([0] + cortes, cortes + [alvo])]
        return self.plano[chave]

    # --- passos ------------------------------------------------------------------
    def iniciar(self):
        ident = self._posicao()
        self._evento("painel_iniciado", versao=self.config.VERSAO, modo_parcela="campanha", parcela=ident)
        self._evento("captura_iniciada", parcela=ident, experimento=EXPERIMENTO)
        self.st.analisador_estado = "analisando"
        self._gravar_status()

    def foto(self):
        """Uma foto na carreira atual; ao completar k fotos, avança."""
        if self.i >= len(self.ordem):
            return False
        x, y, l = chave = self.ordem[self.i]
        corrigido = self._contagens(chave)[self.fotos_na_carreira]
        bruto = round(corrigido * self.config.TAXA_RECALL / self.config.TAXA_PRECISAO)
        t_img = self._agora(self.config.INTERVALO_CAPTURA_S)
        t_an = t_img + timedelta(seconds=0.0 if self.tempo_real else 1.4)
        ident = f"X{x}Y{y}L{l}"
        nome = f"{ident}_{t_img:%Y-%m-%d_%H-%M-%S-%f}.jpg"
        self.registro.registrar_analise(
            self.config.ARQUIVO_CSV, experimento=EXPERIMENTO, parcela=ident, X=x, Y=y, linha=l,
            timestamp_imagem=t_img.strftime("%Y-%m-%d %H:%M:%S.%f"),
            timestamp_analise=t_an.strftime("%Y-%m-%d %H:%M:%S"),
            plantulas_bruto=bruto, plantulas_corrigido=corrigido, nome_imagem=nome,
            versao_modelo=self.config.VERSAO_MODELO, versao_software=self.config.VERSAO,
        )
        if self.st.parcela != ident:
            self.st.parcela, self.st.total_parcela_bruto, self.st.total_parcela_corrigido = ident, 0, 0
        self.st.total_parcela_bruto += bruto
        self.st.total_parcela_corrigido += corrigido
        self.st.plot, self.st.linha = f"X{x}Y{y}", l
        self.st.ultima_imagem, self.st.plantulas_bruto, self.st.plantulas_corrigido = nome, bruto, corrigido
        self._gravar_status()

        self.fotos_na_carreira += 1
        if self.fotos_na_carreira >= self.k:
            self.proxima()
        return True

    def proxima(self):
        de = "X{}Y{}L{}".format(*self.ordem[self.i])
        self.i += 1
        self.fotos_na_carreira = 0
        if self.tempo_real:
            time.sleep(self.manobra_s)                   # manobra até a próxima carreira
        self._agora(20)
        if self.i >= len(self.ordem):
            self._evento("captura_parada", parcela=de, fotos=self.k)
            self.st.analisador_estado = "pronto"
            self._gravar_status()
            return
        para = self._posicao()
        self._evento("parcela_avancada", de=de, para=para, durante_captura=True)
        if self.i % self.sync_a_cada == 0:               # um backup de vez em quando
            self._evento("sync_ok")
            self.io.escrever_texto(self.config.ARQUIVO_ULTIMA_SYNC,
                                   self.relogio.strftime("%Y-%m-%d %H:%M:%S"))

    def historico(self, fracao):
        """Começa a campanha e grava em lote até `fracao` das carreiras (deixa
        a atual pela metade). Ao vivo, o lote termina "agora" e o resto segue
        em tempo real."""
        alvo = int(len(self.ordem) * fracao)
        if self.ao_vivo:
            por_carreira = self.k * self.config.INTERVALO_CAPTURA_S + 20
            self.relogio = datetime.now() - timedelta(seconds=alvo * por_carreira)
        self.iniciar()
        while self.i < alvo:
            self.foto()
        for _ in range(self.k // 2):
            self.foto()
        self.tempo_real = self.ao_vivo


def main(argv=None):
    ap = argparse.ArgumentParser(description="Campanha sintética (DEMO) para a visão 3D.")
    ap.add_argument("--dir", help="pasta da demo (padrão: temporária)")
    ap.add_argument("--snapshot", help="grava o snapshot JSON neste arquivo e sai")
    ap.add_argument("--ao-vivo", action="store_true", help="continua gravando em tempo real")
    ap.add_argument("--progresso", type=float, default=0.45, help="fração já feita ao começar")
    ap.add_argument("--fotos-por-carreira", type=int, default=8)
    ap.add_argument("--intervalo", type=float, default=0.9, help="segundos entre fotos (ao vivo)")
    ap.add_argument("--semente", type=int, default=7)
    ap.add_argument("--manobra", type=float, default=3.0, help="segundos de manobra entre carreiras (ao vivo)")
    ap.add_argument("--inicio", default=INICIO_FIXO.strftime("%Y-%m-%d %H:%M:%S"),
                    help="início da campanha no snapshot estático (ex.: '2026-10-15 17:30:00' para um fim de tarde)")
    args = ap.parse_args(argv)
    if not args.snapshot and not args.ao_vivo:
        ap.error("use --snapshot ARQUIVO e/ou --ao-vivo")

    pasta = os.path.abspath(args.dir or tempfile.mkdtemp(prefix="rover-demo-"))
    camp = Campanha(pasta, random.Random(args.semente), args.ao_vivo, args.fotos_por_carreira, args.manobra,
                    datetime.fromisoformat(args.inicio))
    camp.historico(args.progresso)

    if args.snapshot:
        from core import campo
        snap = campo.montar_snapshot(agora=camp.relogio + timedelta(seconds=2))
        os.makedirs(os.path.dirname(os.path.abspath(args.snapshot)), exist_ok=True)
        with open(args.snapshot, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, separators=(",", ":"))
        print(f"DEMO: snapshot em {args.snapshot} ({snap['kpis']['carreiras_analisadas']} "
              f"carreiras analisadas, {snap['kpis']['carreiras_em_alerta']} em alerta)")

    if args.ao_vivo:
        print(f"DEMO: gravando ao vivo em {pasta} (Ctrl+C para parar)", flush=True)
        try:
            while camp.foto():
                time.sleep(args.intervalo)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
