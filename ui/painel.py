"""
ui/painel.py — a tela (feat/parcela: faixa da amostra + progresso do plot).

Layout em faixas (ver docs/screenshots/mock-painel-v1.png):

    topo (título + pílula de status)
    ┌ Experimento (+ editar) · Parcela (X/Y/Linha · identificador · ◂ Próxima) ┐
    ┌ Contagem ┐  ┌ Progresso da parcela ┐
    ┌ Estado do sistema ┐
    [ Iniciar Captura · F5 ]   [ Sincronizar · F9 ]

A parcela agora é estruturada (experimento + X + Y + linha, ver
`core/parcela.py`). "Próxima" (F2) anda linha 1→2→3→próximo plot: segue a
planilha da semeadora se `config.PLANILHA_PROGRAMACAO` existir (modo
campanha), senão incrementa X/Y nas faixas de config (modo manual). A
posição é persistida — retoma onde parou.

Ver docs/MELHORIAS.md frentes #5 e #6.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
from datetime import datetime
import shutil
import subprocess
import os
import threading
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from core import status as status_mod
from core import parcela as parcela_mod
from core import eventos
from core import watchdog
from core import export as export_mod

from . import tema
from . import widgets


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Estação de Controlo de Captura v{config.VERSAO} - Rover FAPA")
        self.root.geometry("900x720")
        self.root.minsize(860, 660)
        self.root.configure(bg=tema.BG)

        self.capturador_process = None
        self.analyzer_process = None
        self.is_running = False
        self.photo_count = 0
        self.setor_atual = ""

        self.status_file = config.ARQUIVO_STATUS
        self.fontes = tema.Fontes()

        # posição da campanha (planilha se existir, senão modo manual)
        self.nav = parcela_mod.Navegador.do_config()
        self.nav.restaurar()

        # --- topo ---
        top, self._pill = widgets.montar_topo(root, self.fontes)
        top.pack(fill="x", padx=tema.PAD, pady=(16, 10))

        # --- faixa da amostra ---
        amostra, self._am = widgets.montar_amostra(
            root, self.fontes, self.editar_experimento, self.parcela_anterior, self.parcela_proxima)
        amostra.pack(fill="x", padx=tema.PAD, pady=(0, tema.GAP))

        # --- Contagem | Progresso ---
        mainarea = tk.Frame(root, bg=tema.BG)
        mainarea.pack(fill="both", expand=True, padx=tema.PAD)
        mainarea.columnconfigure(0, weight=1, uniform="m")
        mainarea.columnconfigure(1, weight=1, uniform="m")
        mainarea.rowconfigure(0, weight=1)

        cc, self._ct = widgets.montar_contagem(mainarea, self.fontes)
        cc.grid(row=0, column=0, sticky="nsew", padx=(0, tema.GAP // 2))
        pg, self._pg = widgets.montar_progresso(mainarea, self.fontes)
        pg.grid(row=0, column=1, sticky="nsew", padx=(tema.GAP // 2, 0))

        # nomes mantidos p/ compatibilidade dos testes
        self.lbl_total_count = self._ct["lbl_total"]
        self.lbl_bruto = self._ct["lbl_bruto"]
        self.lbl_fila = self._ct["lbl_fila"]

        # --- estado do sistema ---
        sc, self._est = widgets.montar_estado_sistema(root, self.fontes)
        sc.pack(fill="x", padx=tema.PAD, pady=(tema.GAP, tema.GAP))
        self.lbl_current_operacao = self._est["val_captura"]

        # --- ações ---
        acts, self.btn_start_stop, self.btn_sync = widgets.montar_acoes(
            root, self.fontes, self.toggle_capture, self.run_sync)
        acts.pack(fill="x", padx=tema.PAD, pady=(0, 16))

        # --- atalhos ---
        self.root.bind("<F5>", lambda e: self.toggle_capture())
        self.root.bind("<F9>", lambda e: self.run_sync())
        self.root.bind("<F2>", lambda e: self.parcela_proxima())
        self.root.bind("<Control-e>", lambda e: self.exportar_planilha())
        self.root.bind("<Control-q>", lambda e: self.exit_app())

        self._atualizar_parcela_ui()
        self.start_analyzer()
        self.update_dashboard()
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
        eventos.registrar("painel_iniciado", versao=config.VERSAO,
                          modo_parcela=self.nav.modo, parcela=self.nav.identificador())
        watchdog.pronto()

    # =======================================================================
    # parcela / navegação
    # =======================================================================
    def _atualizar_parcela_ui(self):
        am = self._am
        am["lbl_exp"].config(text=self.nav.experimento)
        am["val_x"].config(text=str(self.nav.x))
        am["val_y"].config(text=str(self.nav.y))
        am["val_linha"].config(text=str(self.nav.linha))
        am["lbl_ident"].config(text=self.nav.identificador())
        am["lbl_plot"].config(text=self.nav.rotulo_plot())

    def _salvar_parcela(self):
        try:
            self.nav.salvar()
        except OSError:
            pass

    def editar_experimento(self):
        if self.is_running:
            return
        novo = simpledialog.askstring("Experimento", "Nome do experimento:",
                                      initialvalue=self.nav.experimento, parent=self.root)
        if novo:
            self.nav.experimento = novo.strip()
            self._salvar_parcela()
            self._atualizar_parcela_ui()
            eventos.registrar("experimento_alterado", nome=self.nav.experimento)

    def parcela_proxima(self):
        if self.is_running:
            return
        de = self.nav.identificador()
        self.nav.proxima()
        self._salvar_parcela()
        self._atualizar_parcela_ui()
        eventos.registrar("parcela_avancada", de=de, para=self.nav.identificador())

    def parcela_anterior(self):
        if self.is_running:
            return
        de = self.nav.identificador()
        self.nav.anterior()
        self._salvar_parcela()
        self._atualizar_parcela_ui()
        eventos.registrar("parcela_voltou", de=de, para=self.nav.identificador())

    # =======================================================================
    # dashboard
    # =======================================================================
    def _atualizar_pilula(self, st):
        if self.is_running:
            texto, cor = "capturando", tema.OK
        elif st is None:
            texto, cor = "aguardando analisador", tema.T3
        elif st.analisador_estado == "erro":
            texto, cor = "erro no analisador", tema.STOP
        elif st.analisador_estado == "carregando":
            texto, cor = "carregando modelo…", tema.WARN
        elif st.analisador_estado == "analisando":
            texto, cor = "analisando", tema.OK
        else:
            texto, cor = "sistema pronto", tema.OK
        self._pill["dot"].config(fg=cor)
        self._pill["texto"].config(text=" " + texto)

    def _atualizar_estado_sistema(self, st):
        est = self._est
        if self.is_running:
            est["dot_captura"].config(fg=tema.OK)
            est["val_captura"].config(text="ativa", fg=tema.OK)
        else:
            est["dot_captura"].config(fg=tema.STOP)
            est["val_captura"].config(text="parada", fg=tema.STOP)

        if st is None:
            est["dot_analisador"].config(fg=tema.T3)
            est["val_analisador"].config(text="—", fg=tema.T3)
        else:
            txt, cor = tema.ESTADO_ANALISADOR.get(st.analisador_estado, (st.analisador_estado, tema.T2))
            est["dot_analisador"].config(fg=cor)
            est["val_analisador"].config(text=txt, fg=cor)

        # última sync
        try:
            with open(config.ARQUIVO_ULTIMA_SYNC, encoding="utf-8") as f:
                est["val_sync"].config(text=f.read().strip()[:16] or "nunca")
        except OSError:
            est["val_sync"].config(text="nunca")

        # arquivos aguardando upload (proxy: o que já foi analisado)
        try:
            n = len([x for x in os.listdir(config.PASTA_ANALISADAS) if x.endswith(".jpg")])
        except OSError:
            n = 0
        est["val_pend"].config(text=f"{n} arquivo" + ("s" if n != 1 else ""),
                               fg=tema.WARN if n else tema.T2)

        # rodapé: CPU · disco · versão
        try:
            t = subprocess.check_output(["vcgencmd", "measure_temp"]).decode()
            cpu = t.strip().replace("temp=", "")
        except Exception:
            cpu = "n/d"
        try:
            livre_gb = shutil.disk_usage(config.BASE_DIR).free / 1e9
            disco = f"{livre_gb:.0f} GB livres"
        except OSError:
            disco = "n/d"
        est["lbl_rodape"].config(text=f"CPU {cpu}     ·     Disco {disco}     ·     v{config.VERSAO}")
        # atributos legados usados por testes de telemetria
        self.lbl_temp = est["lbl_rodape"]

    def _atualizar_progresso(self, st):
        pg = self._pg
        plot_corrente = parcela_mod.plot_id(self.nav.x, self.nav.y)
        casa = st is not None and st.plot == plot_corrente
        totais = [st.total_linha_1, st.total_linha_2, st.total_linha_3] if casa else [None, None, None]
        for i, linha_w in enumerate(pg["linhas"], start=1):
            val = totais[i - 1]
            # 0 / None -> "—" (linha ainda não contada); >0 -> o número
            linha_w["val"].config(text=str(val) if val else "—",
                                  fg=tema.T1 if val else tema.T3)
            atual = (i == self.nav.linha)
            linha_w["nome"].config(fg=tema.T1 if atual else tema.T2)
            linha_w["atual"].config(text="● atual" if atual else "")
        total_plot = sum(v for v in totais if v) if casa else 0
        pg["lbl_total_plot"].config(text=str(total_plot))

    def update_dashboard(self):
        st = None
        try:
            st = status_mod.ler(self.status_file)
            if st is not None:
                self.lbl_bruto.config(text=str(st.plantulas_bruto))
                self.lbl_fila.config(
                    text=f"{st.fila_pendente} a analisar" if st.fila_pendente else "vazia",
                    fg=tema.WARN if st.fila_pendente else tema.T2)
                if st.parcela and st.parcela == self.setor_atual:
                    self.lbl_total_count.config(text=str(st.total_parcela_corrigido))
                elif not self.is_running:
                    self.lbl_total_count.config(text=str(st.total_parcela_corrigido))
        except Exception:
            pass

        self._atualizar_pilula(st)
        self._atualizar_estado_sistema(st)
        self._atualizar_progresso(st)

        watchdog.batida()
        self.root.after(2000, self.update_dashboard)

    # =======================================================================
    # captura
    # =======================================================================
    def toggle_capture(self):
        if self.is_running:
            self.stop_capture()
        else:
            self.start_capture()

    def start_capture(self):
        setor_nome = self.nav.identificador()

        self.is_running = True
        self.photo_count = 0
        self.setor_atual = setor_nome

        self.update_gui_state()
        self.lbl_total_count.config(text="0")
        self.lbl_bruto.config(text="--")
        eventos.registrar("captura_iniciada", parcela=setor_nome,
                          experimento=self.nav.experimento)

        python_executable = sys.executable
        command = [python_executable, '-u', config.SCRIPT_CAPTURADOR, '--setor', setor_nome]
        self.capturador_process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        self.listener_thread = threading.Thread(target=self.listen_for_captures, daemon=True)
        self.listener_thread.start()

    def stop_capture(self):
        if self.capturador_process:
            self.capturador_process.terminate()
        self.is_running = False
        self.update_gui_state()
        eventos.registrar("captura_parada", parcela=self.setor_atual,
                          fotos=self.photo_count)

    def listen_for_captures(self):
        if self.capturador_process and self.capturador_process.stdout:
            for line in iter(self.capturador_process.stdout.readline, ''):
                print(f"[Saída do Capturador]: {line.strip()}")
                if "CAPTURED" in line:
                    self.photo_count += 1
            self.capturador_process.stdout.close()

    # =======================================================================
    # sincronização
    # =======================================================================
    def run_sync(self):
        if self.is_running:
            messagebox.showwarning("Atenção", "Pare a captura antes de sincronizar os dados com a nuvem.")
            return
        resposta = messagebox.askyesno(
            "Sincronizar", "Conectado ao Wi-Fi?\nEnviar as imagens novas e o CSV para o Google Drive agora?")
        if resposta:
            threading.Thread(target=self._executar_sincronizacao_background, daemon=True).start()

    def _executar_sincronizacao_background(self):
        self.root.after(0, lambda: self.btn_sync.config(text="⏳ Sincronizando…", state="disabled"))
        try:
            subprocess.run([sys.executable, config.SCRIPT_SINCRONIZAR], check=True)
            self.root.after(0, lambda: messagebox.showinfo(
                "Sucesso", "Backup concluído!\nImagens e relatório CSV seguros no Google Drive."))
        except subprocess.CalledProcessError:
            self.root.after(0, lambda: messagebox.showerror(
                "Erro de Rede", "Falha ao enviar os dados.\nVerifique a internet do Raspberry Pi."))
        finally:
            self.root.after(0, lambda: self.btn_sync.config(text="☁ Sincronizar · F9", state="normal"))

    # =======================================================================
    # exportar planilha (Ctrl+E)
    # =======================================================================
    def exportar_planilha(self):
        if self.is_running:
            messagebox.showwarning("Atenção", "Pare a captura antes de exportar a planilha.")
            return
        ext = os.path.splitext(config.PLANILHA_PROGRAMACAO)[1].lower() or ".xlsx"
        saida = os.path.join(config.BASE_DIR, f"export_{datetime.now():%Y%m%d-%H%M}{ext}")
        try:
            caminho, n = export_mod.exportar(
                saida, caminho_planilha=config.PLANILHA_PROGRAMACAO,
                experimento=self.nav.experimento)
        except (FileNotFoundError, ValueError) as e:
            messagebox.showerror("Exportar", f"Não foi possível exportar:\n{e}")
            return
        eventos.registrar("planilha_exportada", saida=os.path.basename(caminho), plots=n)
        messagebox.showinfo("Exportar",
                            f"{n} plot(s) preenchido(s).\nSalvo em:\n{caminho}")

    # =======================================================================
    def update_gui_state(self):
        nav_state = "disabled" if self.is_running else "normal"
        self._am["btn_ant"].config(state=nav_state)
        self._am["btn_prox"].config(state=nav_state)
        if self.is_running:
            self.btn_start_stop.config(text="⏹ Parar Captura · F5", bg=tema.BOTAO_STOP)
            self.btn_sync.config(state="disabled")
        else:
            self.btn_start_stop.config(text="▶ Iniciar Captura · F5", bg=tema.BOTAO_OK)
            self.btn_sync.config(state="normal")

    def start_analyzer(self):
        print("A iniciar o analisador em segundo plano...")
        self.analyzer_process = subprocess.Popen([sys.executable, config.SCRIPT_ANALISADOR])

    def exit_app(self):
        if messagebox.askokcancel("Sair", "Isso irá parar todos os processos. Deseja continuar?"):
            if self.capturador_process:
                self.capturador_process.terminate()
            if self.analyzer_process:
                self.analyzer_process.terminate()
            self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
