import subprocess
import os
import datetime
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from core import eventos

# ==========================================
# CAMINHOS LOCAIS (ver config.py — derivados de BASE_DIR)
# ==========================================
PASTA_IMAGENS = config.PASTA_ANALISADAS
ARQUIVO_CSV = config.ARQUIVO_CSV

# ==========================================
# CAMINHO NA NUVEM (rclone remote — ver config.py)
# ==========================================
NUVEM_DESTINO_IMAGENS = config.NUVEM_DESTINO_IMAGENS
NUVEM_DESTINO_CSV = config.NUVEM_DESTINO_CSV

def sincronizar():
    agora = datetime.datetime.now().strftime('%H:%M:%S')
    print(f"[{agora}] Iniciando backup para o Google Drive...")
    
    # Comando 1: Sincronizar a pasta de imagens (Ignora as que já subiram)
    comando_imagens = [
        "rclone", "copy", PASTA_IMAGENS, NUVEM_DESTINO_IMAGENS,
        "--update",      
        "--progress",    
        "--transfers=4"  
    ]
    
    # Comando 2: Atualizar o arquivo CSV (Sobrescreve o antigo na nuvem pelo novo)
    comando_csv = [
        "rclone", "copy", ARQUIVO_CSV, NUVEM_DESTINO_CSV,
        "--update",
        "--progress"
    ]
    
    try:
        print("\n--- 1/2: Sincronizando Imagens Analisadas ---")
        subprocess.run(comando_imagens, check=True, text=True)
        
        print("\n--- 2/2: Sincronizando Relatório CSV ---")
        # Só tenta subir o CSV se ele já existir (evita erro no primeiro uso)
        if os.path.exists(ARQUIVO_CSV):
            subprocess.run(comando_csv, check=True, text=True)
        else:
            print(f"Aviso: O arquivo {ARQUIVO_CSV} ainda não foi criado. Pulando etapa.")
            
        try:
            with open(config.ARQUIVO_ULTIMA_SYNC, "w", encoding="utf-8") as f:
                f.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        except OSError:
            pass

        eventos.registrar("sync_ok")
        print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] ✅ Sincronização 100% concluída!")

    except subprocess.CalledProcessError as e:
        eventos.registrar("sync_erro", erro=str(e))
        print(f"\n❌ Erro ao sincronizar. Detalhes: {e}")
        # Retorna código de erro para o painel Tkinter saber que falhou
        sys.exit(1)

if __name__ == "__main__":
    sincronizar()