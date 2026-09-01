import tkinter as tk
from tkinter import messagebox, font
import subprocess
import os
import threading
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from core import status as status_mod

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Estação de Controlo de Captura v{config.VERSAO} - Rover FAPA")
        self.root.geometry("780x580")
        self.root.configure(bg="#f4f4f4") 

        self.capturador_process = None
        self.analyzer_process = None
        self.is_running = False
        self.photo_count = 0

        # Parcela sendo capturada agora. O TOTAL só é exibido quando o status
        # gravado pelo analisador é desta mesma parcela (evita mostrar total
        # antigo de uma parcela anterior).
        self.setor_atual = ""

        self.status_file = config.ARQUIVO_STATUS

        title_font = font.Font(family="Helvetica", size=12, weight="bold")
        label_font = font.Font(family="Helvetica", size=11)
        entry_font = font.Font(family="Helvetica", size=11)
        medium_number_font = font.Font(family="Helvetica", size=32, weight="bold") 
        big_number_font = font.Font(family="Helvetica", size=64, weight="bold")    
        btn_font = font.Font(family="Helvetica", size=12, weight="bold")

        main_frame = tk.Frame(root, padx=20, pady=20, bg="#f4f4f4")
        main_frame.pack(expand=True, fill=tk.BOTH)

        input_frame = tk.LabelFrame(main_frame, text=" Configurações do Experimento ", padx=15, pady=15, bg="#ffffff", font=title_font)
        input_frame.pack(fill="x", expand=False, pady=(0, 15))
        
        tk.Label(input_frame, text="Tratamento:", bg="#ffffff", font=label_font).grid(row=0, column=0, sticky="w", pady=5, padx=(0, 10))
        self.entry_tratamento = tk.Entry(input_frame, width=35, font=entry_font, relief="solid", bd=1)
        self.entry_tratamento.grid(row=0, column=1, pady=5)
        
        tk.Label(input_frame, text="Linha:", bg="#ffffff", font=label_font).grid(row=1, column=0, sticky="w", pady=5, padx=(0, 10))
        self.entry_linha = tk.Entry(input_frame, width=35, font=entry_font, relief="solid", bd=1)
        self.entry_linha.grid(row=1, column=1, pady=5)

        # --- FRAME DE CONTROLO ATUALIZADO ---
        control_frame = tk.Frame(main_frame, bg="#f4f4f4")
        control_frame.pack(fill="x", expand=False, pady=(0, 15))
        
        self.btn_start_stop = tk.Button(control_frame, text="▶ INICIAR CAPTURA", command=self.toggle_capture, bg="#4CAF50", fg="white", font=btn_font, height=2, cursor="hand2", relief="groove")
        self.btn_start_stop.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        # --- NOVO BOTÃO DE SINCRONIZAÇÃO AQUI ---
        self.btn_sync = tk.Button(control_frame, text="☁ SINCRONIZAR NUVEM", command=self.run_sync, bg="#2196F3", fg="white", font=btn_font, height=2, cursor="hand2", relief="groove")
        self.btn_sync.pack(side="left", expand=True, fill="x", padx=5)

        self.btn_exit = tk.Button(control_frame, text="SAIR DO PAINEL", command=self.exit_app, bg="#607D8B", fg="white", font=btn_font, height=2, cursor="hand2", relief="groove")
        self.btn_exit.pack(side="right", expand=True, fill="x", padx=(5, 0))

        dashboard_frame = tk.Frame(main_frame, bg="#f4f4f4")
        dashboard_frame.pack(fill="both", expand=True)

        ia_frame = tk.LabelFrame(dashboard_frame, text=" Visão Computacional (YOLO) ", padx=10, pady=10, bg="#ffffff", font=title_font)
        ia_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        tk.Label(ia_frame, text="Plântulas na Última Foto:", bg="#ffffff", font=label_font, fg="#555555").pack(pady=(5, 0))
        self.lbl_plant_count = tk.Label(ia_frame, text="--", font=medium_number_font, fg="#2196F3", bg="#ffffff")
        self.lbl_plant_count.pack()

        tk.Frame(ia_frame, height=2, bd=1, relief="sunken", bg="#e0e0e0").pack(fill="x", pady=10, padx=20)
        
        tk.Label(ia_frame, text="TOTAL ACUMULADO:", bg="#ffffff", font=font.Font(family="Helvetica", size=14, weight="bold"), fg="#333333").pack(pady=(0, 0))
        self.lbl_total_count = tk.Label(ia_frame, text="0", font=big_number_font, fg="#4CAF50", bg="#ffffff")
        self.lbl_total_count.pack(expand=True)

        telemetria_frame = tk.LabelFrame(dashboard_frame, text=" Telemetria Raspberry Pi ", padx=10, pady=10, bg="#ffffff", font=title_font)
        telemetria_frame.pack(side="right", fill="both", expand=True)

        tk.Label(telemetria_frame, text="Operação Atual:", bg="#ffffff", font=label_font).grid(row=0, column=0, sticky="w", pady=5)
        self.lbl_current_operacao = tk.Label(telemetria_frame, text="Parado", font=font.Font(family="Helvetica", size=11, weight="bold"), fg="#F44336", bg="#ffffff")
        self.lbl_current_operacao.grid(row=0, column=1, sticky="w", pady=5)
        
        tk.Label(telemetria_frame, text="Fotos Capturadas:", bg="#ffffff", font=label_font).grid(row=1, column=0, sticky="w", pady=5)
        self.lbl_photo_count = tk.Label(telemetria_frame, text="0", font=font.Font(family="Helvetica", size=14, weight="bold"), fg="#333333", bg="#ffffff")
        self.lbl_photo_count.grid(row=1, column=1, sticky="w", pady=5)
        
        tk.Frame(telemetria_frame, height=2, bd=1, relief="sunken", bg="#cccccc").grid(row=2, column=0, columnspan=2, sticky="we", pady=10)
        
        tk.Label(telemetria_frame, text="Temp. CPU:", bg="#ffffff", font=label_font).grid(row=3, column=0, sticky="w", pady=2)
        self.lbl_temp = tk.Label(telemetria_frame, text="--", font=label_font, bg="#ffffff")
        self.lbl_temp.grid(row=3, column=1, sticky="w", pady=2)
        
        tk.Label(telemetria_frame, text="Memória GPU:", bg="#ffffff", font=label_font).grid(row=4, column=0, sticky="w", pady=2)
        self.lbl_gpu = tk.Label(telemetria_frame, text="--", font=label_font, bg="#ffffff")
        self.lbl_gpu.grid(row=4, column=1, sticky="w", pady=2)

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
        self.lbl_current_operacao.config(text=setor_nome, fg="#4CAF50")
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
        self.lbl_current_operacao.config(text="Parado", fg="#F44336")

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
        self.root.after(0, lambda: self.btn_sync.config(text="⏳ SINCRONIZANDO...", state="disabled", bg="#9E9E9E"))
        
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
            self.root.after(0, lambda: self.btn_sync.config(text="☁ SINCRONIZAR NUVEM", state="normal", bg="#2196F3"))

    def update_gui_state(self):
        if self.is_running:
            self.btn_start_stop.config(text="⏹ PARAR CAPTURA", bg="#F44336")
            self.btn_sync.config(state="disabled", bg="#9E9E9E") # Desativa botão de nuvem durante a captura
            self.entry_tratamento.config(state="disabled")
            self.entry_linha.config(state="disabled")
        else:
            self.btn_start_stop.config(text="▶ INICIAR CAPTURA", bg="#4CAF50")
            self.btn_sync.config(state="normal", bg="#2196F3")
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

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
