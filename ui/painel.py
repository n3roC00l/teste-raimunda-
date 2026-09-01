"""
ui/painel.py — a tela (era painel_controle.py até refactor/ui-split).

`refactor/ui-split` só reorganiza: a lógica de cada método é idêntica à
versão anterior, só a montagem dos widgets foi movida para
`ui/widgets.py` e as cores/fontes para `ui/tema.py`. Nenhum comportamento
visível deveria mudar — é isso que `tests/test_characterization_painel.py`
verifica.

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
        self.root.geometry("780x580")
        self.root.configure(bg=tema.FUNDO)

        self.capturador_process = None
        self.analyzer_process = None
        self.is_running = False
        self.photo_count = 0

        # Parcela sendo capturada agora. O TOTAL só é exibido quando o status
        # gravado pelo analisador é desta mesma parcela (evita mostrar total
        # antigo de uma parcela anterior).
        self.setor_atual = ""

        self.status_file = config.ARQUIVO_STATUS

        self.fontes = tema.Fontes()

        main_frame = tk.Frame(root, padx=20, pady=20, bg=tema.FUNDO)
        main_frame.pack(expand=True, fill=tk.BOTH)

        input_frame, self.entry_tratamento, self.entry_linha = widgets.montar_configuracoes_experimento(
            main_frame, self.fontes)
        input_frame.pack(fill="x", expand=False, pady=(0, 15))

        control_frame, self.btn_start_stop, self.btn_sync, self.btn_exit = widgets.montar_controles(
            main_frame, self.fontes, self.toggle_capture, self.run_sync, self.exit_app)
        control_frame.pack(fill="x", expand=False, pady=(0, 15))

        dashboard_frame = tk.Frame(main_frame, bg=tema.FUNDO)
        dashboard_frame.pack(fill="both", expand=True)

        ia_frame, self.lbl_plant_count, self.lbl_total_count = widgets.montar_visao_computacional(
            dashboard_frame, self.fontes)
        ia_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        (telemetria_frame, self.lbl_current_operacao, self.lbl_photo_count,
         self.lbl_temp, self.lbl_gpu) = widgets.montar_telemetria(dashboard_frame, self.fontes)
        telemetria_frame.pack(side="right", fill="both", expand=True)

        self.start_analyzer()
        self.update_dashboard()
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

    def update_dashboard(self):
        try:
            temp_output = subprocess.check_output(['vcgencmd', 'measure_temp']).decode()
            self.lbl_temp.config(text=temp_output.strip().replace("temp=", ""))
            gpu_output = subprocess.check_output(['vcgencmd', 'get_mem', 'gpu']).decode()
            self.lbl_gpu.config(text=gpu_output.strip().replace("gpu=", ""))
        except FileNotFoundError:
            self.lbl_temp.config(text="Não é um RPi")
            self.lbl_gpu.config(text="Não é um RPi")
        except Exception:
            self.lbl_temp.config(text="Erro")
            self.lbl_gpu.config(text="Erro")

        # O analisador é a fonte da verdade — o painel só lê e exibe.
        try:
            st = status_mod.ler(self.status_file)
            if st is not None:
                # "Plântulas na Última Foto" = contagem corrigida (não a bruta).
                self.lbl_plant_count.config(text=str(st.plantulas_corrigido))

                # TOTAL ACUMULADO: vem pronto do analisador. Só exibe se for
                # da parcela corrente; senão mantém o "0" do início da captura.
                if st.parcela and st.parcela == self.setor_atual:
                    self.lbl_total_count.config(text=str(st.total_parcela_corrigido))
                elif not self.is_running:
                    self.lbl_total_count.config(text=str(st.total_parcela_corrigido))
        except Exception:
            self.lbl_plant_count.config(text="Err")

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
        self.lbl_current_operacao.config(text=setor_nome, fg=tema.VERDE)
        self.lbl_photo_count.config(text="0")
        self.lbl_total_count.config(text="0")
        self.lbl_plant_count.config(text="--")

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
        self.lbl_current_operacao.config(text="Parado", fg=tema.VERMELHO)

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
            # Roda a função em segundo plano
            threading.Thread(target=self._executar_sincronizacao_background, daemon=True).start()

    def _executar_sincronizacao_background(self):
        # Desativa o botão temporariamente
        self.root.after(0, lambda: self.btn_sync.config(text="⏳ SINCRONIZANDO...", state="disabled", bg=tema.CINZA_DESABILITADO))

        try:
            python_executable = sys.executable
            # Chama o script que criamos na etapa anterior!
            caminho_script = config.SCRIPT_SINCRONIZAR
            subprocess.run([python_executable, caminho_script], check=True)

            self.root.after(0, lambda: messagebox.showinfo("Sucesso", "Backup concluído!\nAs imagens e o relatório CSV já estão seguros no Google Drive."))
        except subprocess.CalledProcessError:
            self.root.after(0, lambda: messagebox.showerror("Erro de Rede", "Falha ao enviar os dados.\nVerifique se o script sincronizar_nuvem.py existe e se o Raspberry Pi está com internet."))
        finally:
            # Libera o botão novamente
            self.root.after(0, lambda: self.btn_sync.config(text="☁ SINCRONIZAR NUVEM", state="normal", bg=tema.AZUL))

    def update_gui_state(self):
        if self.is_running:
            self.btn_start_stop.config(text="⏹ PARAR CAPTURA", bg=tema.VERMELHO)
            self.btn_sync.config(state="disabled", bg=tema.CINZA_DESABILITADO)  # Desativa botão de nuvem durante a captura
            self.entry_tratamento.config(state="disabled")
            self.entry_linha.config(state="disabled")
        else:
            self.btn_start_stop.config(text="▶ INICIAR CAPTURA", bg=tema.VERDE)
            self.btn_sync.config(state="normal", bg=tema.AZUL)
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
