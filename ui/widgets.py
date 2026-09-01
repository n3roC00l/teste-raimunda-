"""
ui/widgets.py — construção dos blocos da tela.

Cada função monta um frame e devolve (frame, *widgets que o App precisa
guardar*). `refactor/ui-split` só move o código de dentro de
`App.__init__` para cá — mesmas classes Tk, mesmas opções, mesmo texto.
Layout novo por cartões é `feat/ui-v1`.

Ver docs/MELHORIAS.md frentes #6 e #7.
"""

import tkinter as tk

from . import tema


def montar_configuracoes_experimento(parent, fontes):
    """Bloco ' Configurações do Experimento ': campos Tratamento e Linha.

    Retorna (frame, entry_tratamento, entry_linha).
    """
    input_frame = tk.LabelFrame(
        parent, text=" Configurações do Experimento ", padx=15, pady=15,
        bg=tema.BRANCO, font=fontes.titulo,
    )

    tk.Label(input_frame, text="Tratamento:", bg=tema.BRANCO, font=fontes.label).grid(
        row=0, column=0, sticky="w", pady=5, padx=(0, 10))
    entry_tratamento = tk.Entry(input_frame, width=35, font=fontes.entrada, relief="solid", bd=1)
    entry_tratamento.grid(row=0, column=1, pady=5)

    tk.Label(input_frame, text="Linha:", bg=tema.BRANCO, font=fontes.label).grid(
        row=1, column=0, sticky="w", pady=5, padx=(0, 10))
    entry_linha = tk.Entry(input_frame, width=35, font=fontes.entrada, relief="solid", bd=1)
    entry_linha.grid(row=1, column=1, pady=5)

    return input_frame, entry_tratamento, entry_linha


def montar_controles(parent, fontes, on_toggle_capture, on_sync, on_exit):
    """Botões Iniciar/Parar Captura, Sincronizar Nuvem, Sair do Painel.

    Retorna (frame, btn_start_stop, btn_sync, btn_exit).
    """
    control_frame = tk.Frame(parent, bg=tema.FUNDO)

    btn_start_stop = tk.Button(
        control_frame, text="▶ INICIAR CAPTURA", command=on_toggle_capture,
        bg=tema.VERDE, fg=tema.BRANCO_TEXTO, font=fontes.botao, height=2,
        cursor="hand2", relief="groove",
    )
    btn_start_stop.pack(side="left", expand=True, fill="x", padx=(0, 5))

    btn_sync = tk.Button(
        control_frame, text="☁ SINCRONIZAR NUVEM", command=on_sync,
        bg=tema.AZUL, fg=tema.BRANCO_TEXTO, font=fontes.botao, height=2,
        cursor="hand2", relief="groove",
    )
    btn_sync.pack(side="left", expand=True, fill="x", padx=5)

    btn_exit = tk.Button(
        control_frame, text="SAIR DO PAINEL", command=on_exit,
        bg=tema.CINZA_SAIR, fg=tema.BRANCO_TEXTO, font=fontes.botao, height=2,
        cursor="hand2", relief="groove",
    )
    btn_exit.pack(side="right", expand=True, fill="x", padx=(5, 0))

    return control_frame, btn_start_stop, btn_sync, btn_exit


def montar_visao_computacional(parent, fontes):
    """Bloco ' Visão Computacional (YOLO) ': Última Foto + TOTAL ACUMULADO.

    Retorna (frame, lbl_plant_count, lbl_total_count).
    """
    ia_frame = tk.LabelFrame(
        parent, text=" Visão Computacional (YOLO) ", padx=10, pady=10,
        bg=tema.BRANCO, font=fontes.titulo,
    )

    tk.Label(
        ia_frame, text="Plântulas na Última Foto:", bg=tema.BRANCO,
        font=fontes.label, fg=tema.CINZA_TEXTO,
    ).pack(pady=(5, 0))
    lbl_plant_count = tk.Label(ia_frame, text="--", font=fontes.numero_medio, fg=tema.AZUL, bg=tema.BRANCO)
    lbl_plant_count.pack()

    tk.Frame(ia_frame, height=2, bd=1, relief="sunken", bg=tema.SEPARADOR_1).pack(fill="x", pady=10, padx=20)

    tk.Label(
        ia_frame, text="TOTAL ACUMULADO:", bg=tema.BRANCO,
        font=fontes.rotulo_forte, fg=tema.CINZA_ESCURO,
    ).pack(pady=(0, 0))
    lbl_total_count = tk.Label(ia_frame, text="0", font=fontes.numero_grande, fg=tema.VERDE, bg=tema.BRANCO)
    lbl_total_count.pack(expand=True)

    return ia_frame, lbl_plant_count, lbl_total_count


def montar_telemetria(parent, fontes):
    """Bloco ' Telemetria Raspberry Pi '.

    Retorna (frame, lbl_current_operacao, lbl_photo_count, lbl_temp, lbl_gpu).
    """
    telemetria_frame = tk.LabelFrame(
        parent, text=" Telemetria Raspberry Pi ", padx=10, pady=10,
        bg=tema.BRANCO, font=fontes.titulo,
    )

    tk.Label(telemetria_frame, text="Operação Atual:", bg=tema.BRANCO, font=fontes.label).grid(
        row=0, column=0, sticky="w", pady=5)
    lbl_current_operacao = tk.Label(
        telemetria_frame, text="Parado", font=fontes.valor_operacao,
        fg=tema.VERMELHO, bg=tema.BRANCO,
    )
    lbl_current_operacao.grid(row=0, column=1, sticky="w", pady=5)

    tk.Label(telemetria_frame, text="Fotos Capturadas:", bg=tema.BRANCO, font=fontes.label).grid(
        row=1, column=0, sticky="w", pady=5)
    lbl_photo_count = tk.Label(
        telemetria_frame, text="0", font=fontes.rotulo_forte,
        fg=tema.CINZA_ESCURO, bg=tema.BRANCO,
    )
    lbl_photo_count.grid(row=1, column=1, sticky="w", pady=5)

    tk.Frame(telemetria_frame, height=2, bd=1, relief="sunken", bg=tema.SEPARADOR_2).grid(
        row=2, column=0, columnspan=2, sticky="we", pady=10)

    tk.Label(telemetria_frame, text="Temp. CPU:", bg=tema.BRANCO, font=fontes.label).grid(
        row=3, column=0, sticky="w", pady=2)
    lbl_temp = tk.Label(telemetria_frame, text="--", font=fontes.label, bg=tema.BRANCO)
    lbl_temp.grid(row=3, column=1, sticky="w", pady=2)

    tk.Label(telemetria_frame, text="Memória GPU:", bg=tema.BRANCO, font=fontes.label).grid(
        row=4, column=0, sticky="w", pady=2)
    lbl_gpu = tk.Label(telemetria_frame, text="--", font=fontes.label, bg=tema.BRANCO)
    lbl_gpu.grid(row=4, column=1, sticky="w", pady=2)

    return telemetria_frame, lbl_current_operacao, lbl_photo_count, lbl_temp, lbl_gpu
