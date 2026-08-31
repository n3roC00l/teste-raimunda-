import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk
import threading
import time
from detector_backend import YoloDetector

# --- CONFIGURAÇÃO ---
# Caminho para o seu melhor modelo .pt
# O caminho é relativo à pasta 'yolov5' que está um nível acima da 'app'
CAMINHO_MODELO = 'yolov5/best.pt'
# --- FIM DA CONFIGURAÇÃO ---

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Detector de Plântulas de Soja")
        self.root.geometry("800x600")

        # Inicializa o backend do detector
        self.detector = YoloDetector(caminho_modelo=CAMINHO_MODELO)
        self.thread_deteccao = None
        self.resultado_deteccao = None

        # --- Widgets da GUI ---
        self.btn_selecionar = tk.Button(root, text="Selecionar Imagem", command=self.selecionar_imagem)
        self.btn_selecionar.pack(pady=10)

        self.lbl_imagem = tk.Label(root)
        self.lbl_imagem.pack(expand=True, fill="both", padx=10, pady=10)

        self.lbl_status = tk.Label(root, text="Por favor, selecione uma imagem para análise.", font=("Helvetica", 12))
        self.lbl_status.pack(pady=10)
        
        self.progresso = ttk.Progressbar(root, orient="horizontal", length=300, mode="indeterminate")

    def selecionar_imagem(self):
        caminho_imagem = filedialog.askopenfilename(
            title="Selecione uma imagem",
            filetypes=(("Imagens JPEG", "*.jpg"), ("Imagens PNG", "*.png"), ("Todos os ficheiros", "*.*"))
        )
        if not caminho_imagem:
            return

        # Mostra a imagem original
        img = Image.open(caminho_imagem)
        img.thumbnail((700, 500))
        foto = ImageTk.PhotoImage(img)
        self.lbl_imagem.config(image=foto)
        self.lbl_imagem.image = foto
        
        # Inicia a deteção numa thread separada para não congelar a GUI
        self.lbl_status.config(text="A processar... Por favor, aguarde.")
        self.progresso.pack(pady=5)
        self.progresso.start()
        
        self.resultado_deteccao = None # Limpa o resultado anterior
        self.thread_deteccao = threading.Thread(target=self.rodar_deteccao_em_thread, args=(caminho_imagem,))
        self.thread_deteccao.start()
        
        # Agenda a verificação do resultado
        self.root.after(100, self.verificar_thread)

    def rodar_deteccao_em_thread(self, caminho_imagem):
        """Esta função é executada na thread de background."""
        imagem, contagem = self.detector.detectar(caminho_imagem)
        self.resultado_deteccao = (imagem, contagem)

    def verificar_thread(self):
        """Verifica se a thread de deteção terminou."""
        if self.thread_deteccao.is_alive():
            # Se ainda está a rodar, verifica novamente daqui a 100ms
            self.root.after(100, self.verificar_thread)
        else:
            # A thread terminou, atualiza a GUI com o resultado
            self.progresso.stop()
            self.progresso.pack_forget()

            if self.resultado_deteccao:
                imagem_final, contagem = self.resultado_deteccao
                
                # Converte o resultado (array NumPy) para uma imagem que o Tkinter pode mostrar
                img = Image.fromarray(imagem_final)
                img.thumbnail((700, 500))
                foto = ImageTk.PhotoImage(img)

                self.lbl_imagem.config(image=foto)
                self.lbl_imagem.image = foto
                self.lbl_status.config(text=f"Análise concluída. Número de plântulas detectadas: {contagem}", font=("Helvetica", 14, "bold"))

if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()
