# Checklist de caracterização em campo (hardware real)

`tests/test_characterization_*.py` cobre a lógica que dá para rodar numa
máquina de desenvolvimento (sem câmera, sem GPU, sem `torch`/`cv2`/
`picamera2`/`rclone`). Três trechos só existem de verdade no Raspberry Pi
com o hardware conectado — **este checklist é a caracterização deles**.

Rode uma vez **antes** de começar o `refactor/ui-split`, para ter um
"antes" registrado, e de novo **depois** de cada PR de risco (`feat/ui-v1`,
`feat/persistencia`, `feat/systemd`), rodando a versão nova **ao lado** da
atual (mesmas imagens de entrada) — ver docs/MELHORIAS.md frente #7
(Sandve et al. 2013, regra 8: guarde resultados intermediários para
comparar).

## 1. `capturador.py` — câmera real

Não pode ser importado fora do Pi (abre a câmera no nível de módulo — ver
`test_import_no_nivel_de_modulo_e_um_achado_de_testabilidade`).

- [ ] Rodar `python capturador.py --setor teste_campo` por 30 s
- [ ] Confere: 1 arquivo `.jpg` a cada `config.INTERVALO_CAPTURA_S` (~0,90 s)
- [ ] Confere: nome do arquivo = `{setor}_{YYYY-MM-DD}_{HH-MM-SS-ffffff}.jpg`
- [ ] Confere: resolução da imagem = `config.RESOLUCAO_CAPTURA` (1280×720)
- [ ] `Ctrl+C` encerra limpo, sem travar a câmera (roda de novo em seguida sem erro de "device busy")
- [ ] Anotar aqui a data/hardware do teste:

  | Data | Pi | Câmera | Resultado |
  |---|---|---|---|

## 2. `analisador_em_background.py` — modelo YOLOv5 real

Os testes automatizados usam um `FakeModel` — nunca chamam
`torch.hub.load` nem o `.pt` de verdade. Isso caracteriza a lógica ao redor
(CSV, status, acumulado), não a inferência em si.

- [ ] Rodar o analisador de verdade contra um lote de imagens conhecido
      (mesmo lote entre versão antiga e nova)
- [ ] Comparar `log_analise_total.csv` linha a linha: mesma `plantulas_detectadas_ia`
      por imagem entre as duas versões (a versão do modelo/pesos não mudou)
- [ ] Comparar `plantulas_ajustadas`: bate com `calcular_contagem_ajustada()`
      pinada em `test_calcular_contagem_ajustada_golden_master`
- [ ] Tempo de carga do modelo (`torch.hub.load`) e de cada inferência —
      registrar para detectar regressão de performance depois do split

  | Data | Lote de imagens | CSV antigo == CSV novo? | Nota |
  |---|---|---|---|

## 3. `sincronizar_nuvem.py` — rclone real

Os testes automatizados substituem `subprocess.run` — nunca chamam
`rclone` de verdade nem tocam a rede.

- [ ] `rclone config` com o remote de `config.RCLONE_REMOTE`
- [ ] Rodar `python sincronizar_nuvem.py` com pasta de imagens de teste
- [ ] Confere: imagens aparecem em `{remote}:{NUVEM_BASE}/imagens_analisadas`
- [ ] Confere: CSV aparece em `{remote}:{NUVEM_BASE}/relatorios`
- [ ] Desligar o Wi-Fi no meio e confirmar que dá erro tratado (sai com
      código 1), não trava o painel

  | Data | Remote | Resultado |
  |---|---|---|
