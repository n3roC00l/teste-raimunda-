# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) ·
versionamento: [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

### testes de caracterização — antes do `refactor/ui-split`

**Adicionado**
- `tests/test_characterization_analisador.py` — golden master de
  `calcular_contagem_ajustada` (fórmula atual pinada) + `analisar_imagem`
  fim-a-fim (CSV, status, acumulado, troca de parcela, caminho de erro) com
  um `FakeModel` injetado (não precisa de `torch`/`cv2` reais).
- `tests/test_characterization_sincronizar.py` — comandos `rclone` exatos
  que `sincronizar()` monta, sem precisar do `rclone` instalado
  (`subprocess.run` substituído).
- `tests/test_characterization_capturador.py` — pin por inspeção de código-
  fonte (formato do nome do arquivo, `--setor` obrigatório); documenta que o
  script não é importável fora do Pi (abre a câmera fora do `if __name__ ==
  "__main__"`).
- `tests/test_characterization_painel.py` — `painel_controle.App` real sob
  Tkinter (`$DISPLAY` existente ou `Xvfb` descartável via `tests/conftest.py`),
  estado inicial dos widgets, `start_capture`/`stop_capture`,
  `update_dashboard` com status válido/de outra parcela/pré-schema/ausente,
  `exit_app`.
- `tests/CHECKLIST-CAMPO.md` — o que só dá para caracterizar no Pi com
  câmera, modelo e `rclone` reais.
- `requirements-dev.txt` (só `pytest`), `pytest.ini`.

**Por quê:** antes de quebrar `painel_controle.py` em `ui/` (`refactor/ui-
split`), travar o comportamento atual como *golden master* — se o split for
"só reorganizar", estes testes continuam passando sem alteração. Suite
total: 47 casos. Ref.: Feathers (2004); Sandve et al. (2013, regra 8).
`docs/MELHORIAS.md` frente #7.

**Comportamento:** nenhum — só testes.

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
