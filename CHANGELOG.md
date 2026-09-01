# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) ·
versionamento: [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

### `refactor/status-schema` — schema único do status_analise.json

**Adicionado**
- `core/status.py` — dataclass `StatusAnalise` (schema versionado), leitura/
  escrita **atômica** (`os.replace` + `fsync`) e rejeição de formato
  incompatível (pré-schema v2.0 ou schema mais novo).
- `core/__init__.py`.
- `tests/test_status.py` — 10 casos: contrato do schema, escrita atômica,
  regra de acumulado, retomada após reinício.

**Corrigido**
- **"TOTAL ACUMULADO" travava em 0.** O analisador gravava
  `ultima_imagem_analisada`/`plantulas_detectadas_ia`; o painel procurava
  `imagem_atual`/`total_plantulas_linha` (que nunca existiam). Agora o
  **analisador mantém o acumulado por parcela** e o painel só lê e exibe.

**Alterado**
- `analisador_em_background.py`: acumula `total_parcela_bruto/corrigido` por
  parcela (zera ao trocar de parcela), retoma o acumulado ao reiniciar,
  reporta `analisador_estado` (`carregando`/`pronto`/`analisando`/`erro`) e
  `fila_pendente`. O cabeçalho do CSV **não muda** (isso é RV-06).
- `painel_controle.py`: "Plântulas na Última Foto" passa a mostrar a contagem
  **corrigida**; o TOTAL vem pronto do status e só aparece se for da parcela
  corrente. Removida a lógica de soma quebrada.

**Comportamento:** muda de propósito (correção de bug). Ref.: Nygard
*Release It!* (single source of truth); Candea & Fox (crash-only).
`docs/MELHORIAS.md` frente #2.

### `refactor/config` — configuração central

**Adicionado**
- `config.py` — ponto único de verdade para caminhos, parâmetros do modelo e
  destino da nuvem. Tudo derivado de `BASE_DIR`; override por `ROVER_*` ou
  `config_local.py`.
- `config_local.example.py` — template de override por máquina.
- `tests/test_config.py` — smoke test do contrato de configuração.

**Alterado**
- `painel_controle.py`, `capturador.py`, `analisador_em_background.py`,
  `sincronizar_nuvem.py` passam a importar `config` — sem caminho absoluto nem
  constante espalhada.
- `sincronizar_nuvem.py`: caminhos `/home/operador/Desktop/Projeto_Soja/...`
  trocados por caminhos derivados de `BASE_DIR`; remote do rclone e pasta na
  nuvem agora configuráveis.
- Título do painel usa `config.VERSAO` (era "v2.5" fixo).
- `.gitignore`: ignora `config_local.py`.

**Comportamento:** sem mudança quando o projeto roda da própria pasta (caso de
produção via `iniciar_aplicacao.sh`). Referência: *Twelve-Factor* fator III;
Parnas (1972). Ver `docs/MELHORIAS.md` frente #1.

---

## [2.0.0] — 2026-08-31

- Marco zero: cópia fiel do sistema v2.0 do rover (backup do Google Drive).
