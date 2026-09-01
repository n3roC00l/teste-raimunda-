"""
ui/painel.py — a tela (feat/ui-v1: sistema visual novo + faixas + atalhos).

Layout em faixas (ver docs/PLANO-PAINEL-v1.md e o mock
docs/screenshots/mock-painel-v1.png):

    topo (título + pílula de status)
    ┌ Configurações do Experimento ┐
    ┌ Contagem ┐ ┌ Estado do sistema ┐
    [ Iniciar Captura · F5 ] [ Sincronizar · F9 ] [ Sair · Ctrl+Q ]

A lógica dos métodos é a mesma de antes; o que mudou é a montagem (agora
via ui/widgets.py), a paleta (ui/tema.py) e:
  - a "Última Foto" mostra a contagem CORRIGIDA + a bruta ("detecção IA");
  - fila de análise e estado real do analisador ficam visíveis
    (`fila_pendente` / `analisador_estado` do core/status.py);
  - atalhos F5 / F9 / Ctrl+Q;
  - telemetria não corta mais texto (sem largura fixa).

A faixa "Parcela" do mock (X/Y/Linha, identificador X3Y7L2, botão
"Próxima") depende de carregar a planilha da semeadora — entra no
`feat/parcela` (RV-02 / RV-06), não aqui.

Ver docs/MELHORIAS.md frentes #6 e #7.
"""

import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import threading
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from core import status as status_mod

from . import tema
from . import widgets


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Estação de Controlo de Captura v{config.VERSAO} - Rover FAPA")
        self.root.geometry("880x600")
        self.root.minsize(820, 560)
        self.root.configure(bg=tema.BG)

        self.capturador_process = None
        self.analyzer_process = None
        self.is_running = False
        self.photo_count = 0

        # Parcela sendo capturada agora. O TOTAL só é exibido quando o status
        # gravado pelo analisador é desta mesma parcela.
        self.setor_atual = ""

        self.status_file = config.ARQUIVO_STATUS
        self.fontes = tema.Fontes()

        # --- topo ---
        top, self.lbl_pill_dot, self.lbl_pill_texto = widgets.montar_topo(root, self.fontes)
        top.pack(fill="x", padx=tema.PAD, pady=(16, 10))

        # --- configurações do experimento ---
        cfg, self.entry_tratamento, self.entry_linha = widgets.montar_configuracoes_experimento(
            root, self.fontes)
        cfg.pack(fill="x", padx=tema.PAD, pady=(0, tema.GAP))

        # --- área principal: 2 colunas ---
        mainarea = tk.Frame(root, bg=tema.BG)
        mainarea.pack(fill="both", expand=True, padx=tema.PAD)
        mainarea.columnconfigure(0, weight=1, uniform="m")
        mainarea.columnconfigure(1, weight=1, uniform="m")
        mainarea.rowconfigure(0, weight=1)

        cc, self.lbl_total_count, self.lbl_plant_count, self.lbl_bruto, self.lbl_fila = \
            widgets.montar_contagem(mainarea, self.fontes)
        cc.grid(row=0, column=0, sticky="nsew", padx=(0, tema.GAP // 2))

        sc, est = widgets.montar_estado_sistema(mainarea, self.fontes)
        sc.grid(row=0, column=1, sticky="nsew", padx=(tema.GAP // 2, 0))
        self._est = est
        self.lbl_current_operacao = est["val_parcela"]  # nome mantido p/ compatibilidade
        self.lbl_photo_count = est["val_fotos"]
        self.lbl_temp = est["lbl_temp"]
        self.lbl_gpu = est["lbl_gpu"]

        # --- ações ---
        acts, self.btn_start_stop, self.btn_sync, self.btn_exit = widgets.montar_acoes(
            root, self.fontes, self.toggle_capture, self.run_sync, self.exit_app)
        acts.pack(fill="x", padx=tema.PAD, pady=(tema.GAP, 16))

        # --- atalhos de teclado ---
        self.root.bind("<F5>", lambda e: self.toggle_capture())
        self.root.bind("<F9>", lambda e: self.run_sync())
        self.root.bind("<Control-q>", lambda e: self.exit_app())

        self.start_analyzer()
        self.update_dashboard()
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

    # -----------------------------------------------------------------------
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
        self.lbl_pill_dot.config(fg=cor)
        self.lbl_pill_texto.config(text=" " + texto)

    def _atualizar_estado_sistema(self, st):
        if self.is_running:
            self._est["dot_captura"].config(fg=tema.OK)
            self._est["val_captura"].config(text="ativa", fg=tema.OK)
        else:
            self._est["dot_captura"].config(fg=tema.STOP)
            self._est["val_captura"].config(text="parada", fg=tema.STOP)

        if st is None:
            self._est["dot_analisador"].config(fg=tema.T3)
            self._est["val_analisador"].config(text="—", fg=tema.T3)
        else:
            texto, cor = tema.ESTADO_ANALISADOR.get(
                st.analisador_estado, (st.analisador_estado, tema.T2))
            self._est["dot_analisador"].config(fg=cor)
            self._est["val_analisador"].config(text=texto, fg=cor)

    def update_dashboard(self):
        try:
            temp_output = subprocess.check_output(['vcgencmd', 'measure_temp']).decode()
            self.lbl_temp.config(text=temp_output.strip().replace("temp=", ""))
            gpu_output = subprocess.check_output(['vcgencmd', 'get_mem', 'gpu']).decode()
            self.lbl_gpu.config(text=gpu_output.strip().replace("gpu=", ""))
        except FileNotFoundError:
            self.lbl_temp.config(text="n/d (não é um RPi)")
            self.lbl_gpu.config(text="n/d")
        except Exception:
            self.lbl_temp.config(text="erro")
            self.lbl_gpu.config(text="erro")

        # O analisador é a fonte da verdade — o painel só lê e exibe.
        st = None
        try:
            st = status_mod.ler(self.status_file)
            if st is not None:
                # última foto: contagem CORRIGIDA (não a bruta) + a bruta ao lado
                self.lbl_plant_count.config(text=str(st.plantulas_corrigido))
                self.lbl_bruto.config(text=str(st.plantulas_bruto))
                self.lbl_fila.config(
                    text=f"{st.fila_pendente} a analisar" if st.fila_pendente else "vazia",
                    fg=tema.WARN if st.fila_pendente else tema.T2,
                )
                # TOTAL: vem pronto do analisador. Só exibe se for da parcela
                # corrente; senão mantém o "0" do início da captura.
                if st.parcela and st.parcela == self.setor_atual:
                    self.lbl_total_count.config(text=str(st.total_parcela_corrigido))
                elif not self.is_running:
                    self.lbl_total_count.config(text=str(st.total_parcela_corrigido))
        except Exception:
            self.lbl_plant_count.config(text="err")

        self._atualizar_pilula(st)
        self._atualizar_estado_sistema(st)
        self.lbl_photo_count.config(text=str(self.photo_count))

        self.root.after(2000, self.update_dashboard)

    def toggle_capture(self):
        if self.is_running:
            self.stop_capture()
        else:
            self.start_capture()

    def start_capture(self):
        tratamento = self.entry_tratamento.get()
        linha = self.entry_linha.get()

        if not tratamento or not linha:
            messagebox.showerror("Erro", "Os campos Tratamento e Linha devem ser preenchidos.")
            return

        setor_nome = f"trat_{tratamento}_linha_{linha}".replace(" ", "_")

        self.is_running = True
        self.photo_count = 0
        self.setor_atual = setor_nome

        self.update_gui_state()
        self.lbl_current_operacao.config(text=setor_nome, fg=tema.ACC)
        self.lbl_photo_count.config(text="0")
        self.lbl_total_count.config(text="0")
        self.lbl_plant_count.config(text="--")
        self.lbl_bruto.config(text="--")

        python_executable = sys.executable
        caminho_capturador = config.SCRIPT_CAPTURADOR
        command = [python_executable, '-u', caminho_capturador, '--setor', setor_nome]

        self.capturador_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        self.listener_thread = threading.Thread(target=self.listen_for_captures, daemon=True)
        self.listener_thread.start()

    def stop_capture(self):
        if self.capturador_process: self.capturador_process.terminate()
        self.is_running = False
        self.update_gui_state()
        self.lbl_current_operacao.config(text="—", fg=tema.T3)

    def listen_for_captures(self):
        if self.capturador_process and self.capturador_process.stdout:
            for line in iter(self.capturador_process.stdout.readline, ''):
                print(f"[Saída do Capturador]: {line.strip()}")

                if "CAPTURED" in line:
                    self.photo_count += 1
                    self.root.after(0, lambda: self.lbl_photo_count.config(text=str(self.photo_count)))
            self.capturador_process.stdout.close()

    # --- LÓGICA DO BOTÃO DE SINCRONIZAÇÃO ---
    def run_sync(self):
        if self.is_running:
            messagebox.showwarning("Atenção", "Pare a captura antes de sincronizar os dados com a nuvem.")
            return

        resposta = messagebox.askyesno("Sincronizar", "Conectado ao Wi-Fi?\nDeseja enviar as imagens novas e o CSV atualizado para o Google Drive agora?")
        if resposta:
            threading.Thread(target=self._executar_sincronizacao_background, daemon=True).start()

    def _executar_sincronizacao_background(self):
        self.root.after(0, lambda: self.btn_sync.config(text="⏳ Sincronizando…", state="disabled"))

        try:
            python_executable = sys.executable
            caminho_script = config.SCRIPT_SINCRONIZAR
            subprocess.run([python_executable, caminho_script], check=True)

            self.root.after(0, lambda: messagebox.showinfo("Sucesso", "Backup concluído!\nAs imagens e o relatório CSV já estão seguros no Google Drive."))
        except subprocess.CalledProcessError:
            self.root.after(0, lambda: messagebox.showerror("Erro de Rede", "Falha ao enviar os dados.\nVerifique se o script sincronizar_nuvem.py existe e se o Raspberry Pi está com internet."))
        finally:
            self.root.after(0, lambda: self.btn_sync.config(text="☁ Sincronizar · F9", state="normal"))

    def update_gui_state(self):
        if self.is_running:
            self.btn_start_stop.config(text="⏹ Parar Captura · F5", bg=tema.BOTAO_STOP)
            self.btn_sync.config(state="disabled")
            self.entry_tratamento.config(state="disabled")
            self.entry_linha.config(state="disabled")
        else:
            self.btn_start_stop.config(text="▶ Iniciar Captura · F5", bg=tema.BOTAO_OK)
            self.btn_sync.config(state="normal")
            self.entry_tratamento.config(state="normal")
            self.entry_linha.config(state="normal")

    def start_analyzer(self):
        python_executable = sys.executable
        caminho_analisador = config.SCRIPT_ANALISADOR
        print("A iniciar o analisador em segundo plano...")
        self.analyzer_process = subprocess.Popen([python_executable, caminho_analisador])

    def exit_app(self):
        if messagebox.askokcancel("Sair", "Isso irá parar todos os processos. Deseja continuar?"):
            if self.capturador_process: self.capturador_process.terminate()
            if self.analyzer_process: self.analyzer_process.terminate()
            self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
