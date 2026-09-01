# Estado do projeto — onde estamos

Atualizado: 2026-09-01. Base: `v2.0` (marco zero) → em `v2.1.0-dev`.
Histórico completo em [`../CHANGELOG.md`](../CHANGELOG.md).
Plano e embasamento: [`MELHORIAS.md`](MELHORIAS.md).

## Feito (10 PRs mergeados em `main`)

| PR | O que entregou | Frente |
|---|---|---|
| `refactor/config` | `config.py` — ponto único de verdade; zero caminho absoluto | #1 |
| `refactor/status-schema` | `core/status.py` schema único; **conserta o "TOTAL ACUMULADO" travado em 0** | #2 |
| `test/caracterizacao` | golden master do pipeline antes de refatorar (Feathers) | #7 |
| `refactor/ui-split` | painel dividido em `ui/` (comportamento idêntico) | #6 |
| `feat/ui-v1` | tema por tokens, layout em faixas, pílula de status, fila visível, estado real do analisador, atalhos F5/F9/Ctrl+Q | #6 |
| `feat/parcela` | parcela estruturada `X3Y7L2`, navegação "Próxima" (planilha ou aritmético), card "Progresso da parcela", posição persistida | #5 |
| `feat/persistencia`+`feat/systemd` | log de eventos append-only, watchdog sd_notify, `deploy/rover.service` (autostart + reinício) | #3 |
| `feat/export-csv` | CSV canônico *tidy* + `exportar_planilha.py` / Ctrl+E (preenche `linha 1/2/3` da planilha da semeadora) | #2/#5 |
| `feat/troca-carreira-ao-vivo` | trocar de carreira **sem parar a câmera** (F2 durante a captura) | #5 |

**Testes:** 101 casos (`pytest tests/ -q`), rodam sem câmera/GPU/torch/rclone.

## Falta

### Depende do Leandro
- **Fechar a nomenclatura.** Modelo de planilha pronto para enviar:
  `Rover/referencia/anexos/Programação DDP — MODELO ROVER (exemplo).xlsx`.
  Perguntas em aberto: X vs Y (as abas Plan1 e Planilha1 divergem), formato
  exato do identificador, ordem física das 3 carreiras, colunas do retorno. (RV-02, RV-06)
- **Conta de nuvem** para o backup (`rclone`) — autorização de uso do Drive. (RV-04)
- **SSID + senha** do Wi-Fi do local. (RV-05)

### Depende de ir a campo
- **RV-08 — validação da contagem.** Contar carreiras à mão em N parcelas,
  comparar com o rover (Bland–Altman + CCC), trocar o fator fixo `P/R` por
  uma curva de calibração, preencher a coluna `incerteza` do CSV. É o que dá
  base estatística ao resultado.

### Depende de acesso ao Raspberry Pi (RV-07)
- Clonar o repo na conta `operador`, criar `venv`, clonar `yolov5` + pesos.
- `./deploy/install.sh` + autologin gráfico (`raspi-config`).
- Rodar o `tests/CHECKLIST-CAMPO.md` (câmera, modelo, sync reais).
- Provisionar a conta `nero` (admin).

### Dá para fazer agora (sem depender de ninguém)
- **Model Card do YOLOv5** em `docs/` — dataset de treino, condições cobertas,
  desempenho por condição, limitações. (frente #4, parte que não precisa de campo)
- **Tag `v2.1.0`** quando estabilizar em campo. (frente #8)

### Fora do software (outras pessoas)
- **RV-01** eixo móvel traseiro — mecânica (reunião com o Leandro).
- **RV-03** case do display — com o Felipe.

## Backlog RV — status

| ID | Item | Categoria | Status |
|----|------|-----------|--------|
| RV-01 | Eixo móvel traseiro | Mecânica | aberto |
| RV-02 | Troca automática de parcela | Software | **software pronto** · falta confirmar formato c/ Leandro |
| RV-03 | Case móvel do display | Mecânica | com o Felipe |
| RV-04 | Sincronização em nuvem | Infra | script pronto · falta conta/autorização |
| RV-05 | Pré-configuração de Wi-Fi | Infra | aberto (falta SSID/senha) |
| RV-06 | Padronização da nomenclatura | Dados | **CSV + export prontos** · falta confirmar formato c/ Leandro |
| RV-07 | Provisionar o Pi 5 | Infra | `deploy/` pronto · falta rodar no Pi |
| RV-08 | Protocolo de validação da contagem | Dados | aberto — **precisa de ida a campo** |
