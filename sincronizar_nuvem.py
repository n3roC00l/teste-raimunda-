import subprocess
import os
import datetime
import sys

# ==========================================
# CAMINHOS LOCAIS NO RASPBERRY PI
# ==========================================
PASTA_IMAGENS = "/home/operador/Desktop/Projeto_Soja/imagens_analisadas"
ARQUIVO_CSV = "/home/operador/Desktop/Projeto_Soja/logs_analise/log_analise_total.csv"

# ==========================================
# CAMINHO NA NUVEM (GOOGLE DRIVE)
# ==========================================
# O rclone vai criar essa pasta principal 'Rover_FAPA_Backups' lá no seu Drive
NUVEM_DESTINO_IMAGENS = "gdrive:Rover_FAPA_Backups/imagens_analisadas"
NUVEM_DESTINO_CSV = "gdrive:Rover_FAPA_Backups/relatorios"

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
            
        print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] ✅ Sincronização 100% concluída!")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erro ao sincronizar. Detalhes: {e}")
        # Retorna código de erro para o painel Tkinter saber que falhou
        sys.exit(1) 

if __name__ == "__main__":
    sincronizar()