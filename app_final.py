import tkinter as tk
from tkinter import filedialog, messagebox, font, ttk
from PIL import Image, ImageTk
import subprocess
import os
import threading
from detector_backend import YoloDetector

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Analisador de Plântulas de Soja v1.0")
        self.root.geometry("800x700")

        # --- Inicialização do Backend ---
        # O caminho é relativo a esta pasta (Projeto_Soja)
        caminho_modelo = os.path.join('yolov5', 'best.pt')
        self.detector = YoloDetector(caminho_modelo=caminho_modelo)
        self.thread_deteccao = None
        self.resultado_deteccao = None

        # --- Widgets da GUI ---
        main_frame = tk.Frame(root, padx=15, pady=15)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Frame de Controlo
        control_frame = tk.Frame(main_frame, pady=10)
        control_frame.pack(fill="x", expand=False)
        
        self.btn_selecionar = tk.Button(control_frame, text="Selecionar Imagem para Análise", command=self.selecionar_e_analisar, bg="#007BFF", fg="white", font=font.Font(size=12, weight='bold'), height=2)
        self.btn_selecionar.pack(fill="x", expand=True)

        # Frame da Imagem
        image_frame = tk.LabelFrame(main_frame, text="Visualizador", padx=10, pady=10)
        image_frame.pack(fill="both", expand=True)
        self.lbl_imagem = tk.Label(image_frame)
        self.lbl_imagem.pack(expand=True, fill="both")

        # Frame de Status (Dashboard)
        status_frame = tk.LabelFrame(main_frame, text="Dashboard", padx=10, pady=10)
        status_frame.pack(fill="x", expand=False, pady=10)
        
        tk.Label(status_frame, text="Status:").grid(row=0, column=0, sticky="w")
        self.lbl_status = tk.Label(status_frame, text="Aguardando imagem...", font=("Helvetica", 10), fg="blue")
        self.lbl_status.grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(status_frame, text="Plântulas Detectadas:").grid(row=1, column=0, sticky="w")
        self.lbl_plant_count = tk.Label(status_frame, text="0", font=("Helvetica", 14, "bold"))
        self.lbl_plant_count.grid(row=1, column=1, sticky="w", padx=5)
        
        tk.Label(status_frame, text="Temperatura do CPU:").grid(row=2, column=0, sticky="w")
        self.lbl_temp = tk.Label(status_frame, text="N/A", font=("Helvetica", 10))
        self.lbl_temp.grid(row=2, column=1, sticky="w", padx=5)
        
        self.progresso = ttk.Progressbar(status_frame, orient="horizontal", length=200, mode="indeterminate")
        self.progresso.grid(row=0, column=2, padx=20, sticky="e")
        status_frame.grid_columnconfigure(2, weight=1) # Faz a barra de progresso expandir

        # Inicia o loop de atualização do dashboard
        self.update_dashboard()

    def update_dashboard(self):
        try:
            temp_output = subprocess.check_output(['vcgencmd', 'measure_temp']).decode()
            self.lbl_temp.config(text=temp_output.strip().replace("temp=", ""))
        except Exception:
            self.lbl_temp.config(text="N/A (Apenas no Pi)")
        self.root.after(5000, self.update_dashboard) # Atualiza a cada 5 segundos

    def selecionar_e_analisar(self):
        caminho_imagem = filedialog.askopenfilename(
            title="Selecione uma imagem",
            filetypes=(("Imagens", "*.jpg *.jpeg *.png"), ("Todos os ficheiros", "*.*"))
        )
        if not caminho_imagem:
            return

        self.lbl_status.config(text="A processar...", fg="orange")
        self.lbl_plant_count.config(text="...")
        self.progresso.grid(row=0, column=2, padx=20, sticky="e")
        self.progresso.start()
        
        self.thread_deteccao = threading.Thread(target=self.rodar_deteccao_em_thread, args=(caminho_imagem,))
        self.thread_deteccao.start()
        self.root.after(100, self.verificar_thread)

    def rodar_deteccao_em_thread(self, caminho_imagem):
        imagem, contagem = self.detector.detectar(caminho_imagem)
        self.resultado_deteccao = (imagem, contagem)

    def verificar_thread(self):
        if self.thread_deteccao.is_alive():
            self.root.after(100, self.verificar_thread)
        else:
            self.progresso.stop()
            self.progresso.grid_forget()
            if self.resultado_deteccao:
                imagem_final, contagem = self.resultado_deteccao
                
                img = Image.fromarray(imagem_final)
                img.thumbnail((self.lbl_imagem.winfo_width(), self.lbl_imagem.winfo_height()))
                foto = ImageTk.PhotoImage(img)

                self.lbl_imagem.config(image=foto)
                self.lbl_imagem.image = foto
                self.lbl_status.config(text="Análise concluída!", fg="green")
                self.lbl_plant_count.config(text=str(contagem))

if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()
