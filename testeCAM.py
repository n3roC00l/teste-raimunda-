import cv2
from picamera2 import Picamera2
import time

# --- INICIALIZAÇÃO ---
try:
    print("A iniciar a câmera para pré-visualização...")
    picam2 = Picamera2()

    # Configura a câmera para um modo de pré-visualização.
    # Uma resolução de 720p é boa para um feed rápido e de qualidade suficiente para o ajuste.
    config = picam2.create_preview_configuration(main={"size": (1280, 720)})
    picam2.configure(config)

    # Inicia a câmera
    picam2.start()

    # Adiciona uma pequena pausa para a câmera 'aquecer' e ajustar os parâmetros automáticos (foco, exposição)
    time.sleep(2)

    print("\n--- PRÉ-VISUALIZAÇÃO ATIVA ---")
    print(">>> Pressione a tecla 'q' na janela da câmera para sair. <<<")

    # --- LOOP DE VISUALIZAÇÃO ---
    while True:
        # Captura um quadro da câmera como um array numpy.
        # O formato BGR é o padrão que o OpenCV espera para exibir cores corretamente.
        frame = picam2.capture_array()

        # Mostra o quadro numa janela do OpenCV.
        cv2.imshow("Ajuste de Lente - Pressione 'q' para sair", frame)

        # Verifica a cada 1 milissegundo se uma tecla foi pressionada.
        # Se a tecla for 'q', o loop é interrompido.
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except Exception as e:
    print(f"\n!!! Ocorreu um erro ao tentar iniciar a câmera: {e}")
    print("Verifique se a câmera está conectada corretamente e não está em uso por outro programa.")

finally:
    # --- LIMPEZA ---
    print("\nA encerrar a pré-visualização...")
    # Para o feed da câmera de forma segura
    if 'picam2' in locals() and picam2.is_open:
        picam2.stop()
    
    # Fecha todas as janelas abertas pelo OpenCV
    cv2.destroyAllWindows()
    print("Programa encerrado.")
