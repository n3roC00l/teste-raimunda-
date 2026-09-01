# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) ·
versionamento: [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

### `feat/parcela` — parcela estruturada + navegação + progresso do plot

**Adicionado**
- `core/parcela.py` — `Parcela` (experimento + X + Y + linha), `identificador`
  (`X{x}Y{y}L{linha}`, configurável em `config.PARCELA_FORMATO`),
  `parse_identificador`, `carregar_plots` (Plan1 em .csv/.xlsx) e `Navegador`
  (modo campanha = segue a planilha; modo manual = incremento aritmético;
  persiste a posição, retoma onde parou).
- `tests/test_parcela.py` (12 casos).
- Config: `PARCELA_FORMATO` / `PLOT_FORMATO`, faixas `PARCELA_X/Y_MIN/MAX`,
  `PARCELA_LINHAS`, `PLANILHA_PROGRAMACAO`, `ARQUIVO_PARCELA`,
  `EXPERIMENTO_PADRAO`, `ARQUIVO_ULTIMA_SYNC`.

**Alterado**
- `core/status.py` **schema 2**: `experimento`, `plot`, `linha`,
  `total_linha_1/2/3`, `total_plot_corrigido` (property). `ler()` aceita
  schema 1 (upgrade transparente).
- `analisador_em_background.py` — além do acumulado por parcela, agora
  **acumula por linha dentro do plot** (parseia `X3Y7L2` → plot `X3Y7`,
  linha 2). Nomes antigos (`trat_A_linha_1`) continuam funcionando (sem
  progresso por linha). CSV inalterado (RV-06).
- `ui/` — faixa da amostra (Experimento + `editar`; Parcela: X/Y/Linha,
  identificador, `plot N de M`, ◂ / **Próxima ▸ F2**), card **Progresso da
  parcela** (linha 1/2/3 + total do plot), Estado do sistema com **última
  sync** + **aguardando sync** + **disco livre**. Campos livres
  Tratamento/Linha saíram — a parcela agora vem do navegador. Navegação
  travada durante a captura.
- `sincronizar_nuvem.py` grava `logs_analise/ultima_sync.txt` no sucesso.
- `requirements.txt`: `openpyxl` (só p/ planilha .xlsx).

**Comportamento:** muda (nova forma de escolher a parcela). A máquina de
estados de captura e a regra do TOTAL por parcela continuam iguais e
testadas. `tests/test_characterization_painel.py` reescrito para o novo
modelo. Suite: 71 casos. Verificado por screenshot headless (Xvfb) em modo
campanha. `docs/MELHORIAS.md` frentes #5 e #6; RV-02 / RV-06.

### `feat/ui-v1` — sistema visual novo + faixas + atalhos

**Alterado (visual — muda o que o operador vê)**
- `ui/tema.py` — paleta por tokens, tema escuro (`BG`/`BG2`/`LINE` ·
  `T1`/`T2`/`T3` · `ACC` · `OK`/`WARN`/`STOP`), como no plano e no mock
  `docs/screenshots/mock-painel-v1.png`. Cor só significa status; ACC só no
  acento. Ref.: High Performance HMI Handbook / ISA-101.
- `ui/widgets.py` — reescrito em blocos de cartão (`cartao`, `titulo_secao`,
  `linha_kv`, `linha_kv_status`) + `montar_topo/contagem/estado_sistema/acoes`.
- `ui/painel.py` — layout em faixas: topo (título + **pílula de status**) →
  Configurações do Experimento → **Contagem** \| **Estado do sistema** →
  ações. Novidades funcionais:
  - "última foto" mostra a contagem **corrigida** + a **bruta** ("detecção IA");
  - **fila de análise** visível (`fila_pendente`), âmbar quando > 0;
  - **estado real do analisador** na pílula e no cartão
    (`carregando modelo… / pronto / analisando / erro`) — fecha
    `feat/estado-analisador`, já que o analisador reporta desde `status-schema`;
  - **atalhos** F5 (iniciar/parar) · F9 (sincronizar) · Ctrl+Q (sair);
  - telemetria não corta mais texto (sem largura fixa);
  - janela redimensionável, mínimo 820×560.

**Fora de escopo (fica para `feat/parcela` — RV-02/RV-06)**
- Faixa "Parcela" do mock: campos X/Y/Linha, identificador `X3Y7L2`, botão
  "Próxima", card "Progresso da parcela" com linha 1/2/3. Depende de carregar
  a planilha da semeadora — o painel ainda usa os campos Tratamento + Linha
  de hoje.

**Comportamento não-visual:** inalterado. `tests/test_characterization_painel.py`
atualizado para o novo golden master (valores de texto/cor); a máquina de
estados de captura e a regra do TOTAL por parcela continuam iguais e
testadas. Suite: 50 casos. Verificado por screenshot headless (Xvfb).
`docs/MELHORIAS.md` frente #6.

### `refactor/ui-split` — painel dividido em `ui/`

**Adicionado**
- `ui/painel.py` — a classe `App` (movida de `painel_controle.py`, lógica
  idêntica método a método).
- `ui/widgets.py` — 4 funções que montam cada bloco da tela (Configurações
  do Experimento, Controles, Visão Computacional, Telemetria); mesmas
  classes Tk, mesmas opções, mesmo texto de antes.
- `ui/tema.py` — cores (hex idênticos ao original) e fontes centralizadas
  em `Fontes` (uma instância por `App`, precisa de um `tk.Tk()` já criado).

**Alterado**
- `painel_controle.py` virou um shim: `from ui.painel import App, main`;
  `./iniciar_aplicacao.sh` continua funcionando sem mudança.
- `tests/test_characterization_painel.py` passa a importar `ui.painel` em
  vez de `painel_controle` (o resto do arquivo — todos os asserts — não
  mudou uma linha).

**Comportamento:** nenhum. Verificado: suite completa (47 casos) passa sem
alterar nenhuma asserção; screenshot headless (Xvfb) do painel rodado via
`python painel_controle.py` é visualmente idêntico ao de antes do split.
`docs/MELHORIAS.md` frentes #6 e #7 (Parnas 1972 — separar o que muda
[layout, `feat/ui-v1`] do que não muda agora).

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
