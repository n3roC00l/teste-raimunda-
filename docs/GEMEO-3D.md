# Gêmeo digital do ensaio (visão 3D)

Uma visão 3D, **só de leitura**, do campo experimental: os plots da planilha
da semeadora, as 3 carreiras de cada um, o rover e a contagem. Ela é
alimentada pelos arquivos que o sistema já grava; o pipeline de captura e
análise não muda.

Inspiração: a demo *WareTrack* de Dilum Sanjaya (React Three Fiber). Daquela
demo vem a ideia central, **modelo de dados primeiro e o 3D como só mais uma
visão**. Do que ela fazia de errado (relógio "ao vivo" acelerado, histórico
recalculado a partir de "agora", painéis que se contradiziam, posição de
objetos que ninguém mede) vêm as regras abaixo.

## Regras

1. **Dados primeiro.** A visão só desenha o que está no snapshot.
2. **Um lugar só calcula indicador:** `core/campo.py`. A visão não soma nada,
   então dois blocos da tela nunca discordam.
3. **Horário vem do arquivo** (CSV, `eventos.jsonl`) e nunca é recalculado.
   "Agora" só entra nas idades (`idade_*_s`).
4. **Só o medido.** Não há odômetro/GPS nem as caixas do YOLO gravadas: não
   existe posição ao longo da carreira nem posição de planta. A posição do
   rover é ESTIMADA e as plantas desenhadas têm a QUANTIDADE contada e posição
   ilustrativa; a legenda diz as duas coisas. Cenário (carros, nuvens, aves,
   lavouras vizinhas) também vem rotulado.
5. **Status só em exceção** (frente #6 do `MELHORIAS.md`): âmbar/vermelho
   são reservados a alerta, acima dos limiares escritos em `config.py`, e
   alerta nunca é só cor (moldura, bandeirinha, pino, texto). O verde do modo
   Lavoura é a lavoura desenhada (a densidade é o dado), não um status; o modo
   Estado continua neutro como o painel Tkinter.
6. **Só leitura.** A visão não comanda o rover. Operar continua sendo no
   painel Tkinter.

## Arquitetura

```
 Pi 5 (já existe)                        novo
 +-------------------------------+      +---------------------------+
 | capturador > analisador > CSV |      | core/campo.py             |
 | status.json, parcela.json     | ---> | monta o snapshot do       |
 | eventos.jsonl, Plan1, fotos   |      | ensaio (só leitura)       |
 +-------------------------------+      +-------------+-------------+
                                                      | JSON
                        +-----------------------------+--------------+
                        v                                            v
           servidor_visao.py (Pi, rede local)          exportar_gemeo.py
           HTTP só leitura                             HTML único com os dados
                        |                                            |
                        v                                            v
           tablet/notebook no campo                    escritório, estande
              (web/: React + React Three Fiber + drei + zustand)
```

## O snapshot (`core/campo.py`, schema 1)

```bash
python -m core.campo                      # JSON indentado do experimento atual
python -m core.campo --experimento "Safra 2024" --compacto --sem-telemetria
```

| Chave | O que é |
|---|---|
| `schema`, `gerado_em`, `versao_software` | versão do formato, relógio do Pi, versão do código |
| `demo` | `true` se existir o arquivo `DEMO` ao lado do CSV (dados de demonstração) |
| `experimento`, `experimentos`, `campanha_atual` | o mostrado, todos os conhecidos, e se é a campanha do painel |
| `fontes` | de onde veio: planilha usada, linhas do CSV, linhas sem parcela (nome antigo), fora da grade |
| `campo` | geometria em metros (`u` transversal às carreiras, `v` ao longo) e a lista `plots` |
| `campo.plots[].carreiras[]` | por carreira: estado, contagem, esperado, emergência, nº de fotos, horários, sync/export, versões, alerta |
| `rover` | posição (só na campanha atual e se o painel já gravou), captura ligada, analisador, fila, última foto, alertas |
| `kpis` | totais calculados uma vez só (batem com a soma dos plots) |
| `saude` | telemetria do Pi (temperatura, disco, processos vivos) e alertas de disco/backup |
| `limiares`, `nota_contagem` | os limiares em vigor e o aviso sobre o que a contagem significa |
| `eventos` | os últimos `CAMPO_EVENTOS_LIMITE` eventos (linha do tempo) |

### Definições

- **Esperado (carreira)** = `Grãos por Parcela` ÷ carreiras por plot.
- **Emergência** = plantas contadas (corrigido) ÷ esperado. Só existe quando a
  planilha traz os grãos.
- **Plantas (KPI)** = soma das carreiras **fechadas** (`analisada`). A carreira
  em captura é parcial e aparece à parte em `plantulas_em_captura`; ela também
  não dispara alerta enquanto está sendo capturada.
- **Capturando** = o último evento entre `captura_iniciada`, `captura_parada` e
  `painel_iniciado` é `captura_iniciada`.
- **Linhagem da carreira** = capturada (primeira/última foto) → analisada →
  sincronizada (primeiro `sync_ok` depois da última análise) → exportada
  (primeiro `planilha_exportada` depois da última análise).

### Limiares (provisórios: fechar com o Leandro)

| `config.py` | Padrão | Dispara |
|---|---|---|
| `CAMPO_EMERGENCIA_CRITICO` | 0.50 | crítico abaixo disto (e contagem zero) |
| `CAMPO_EMERGENCIA_ATENCAO` | 0.70 | atenção abaixo disto |
| `CAMPO_EMERGENCIA_MAXIMA` | 1.20 | atenção acima disto (dupla contagem? planilha errada?) |
| `CAMPO_FILA_ATENCAO` | 20 | fotos esperando análise |
| `CAMPO_STATUS_VELHO_S` | 30 | captura ligada e o analisador sem gravar status |
| `CAMPO_SYNC_VELHA_S` | 7200 | último backup na nuvem |
| `CAMPO_DISCO_ATENCAO_GB` / `_CRITICO_GB` | 5 / 1 | disco livre |

### Geometria

Vem da Plan1 (`Comprimento Parcela (cm)`, `Passagem (cm)`, `Espaçam. fil
(cm)`, `Carreiras por parcela`) ou, sem planilha, de `CAMPO_*_CM`. Padrão: X
anda transversal às carreiras e Y ao longo delas, como dizem os nomes das
colunas. **Ainda em aberto com o Leandro** (as abas Plan1 e Planilha1
divergem): `ROVER_CAMPO_TROCAR_EIXOS=1` inverte. O próprio mapa 3D serve para
validar com ele.

### Desempenho

O CSV e o `eventos.jsonl` só crescem. `campo.Cache` lê apenas as linhas novas
desde a última chamada (e relê a planilha só quando ela muda). Medido numa
campanha inteira (216 plots, ~9,7 mil fotos): ~100 ms sem cache, ~13 ms com
cache. JSON compacto ~330 KB, ~18 KB com gzip.

## O servidor (`servidor_visao.py`)

```bash
python servidor_visao.py                 # 0.0.0.0:8080; mostra os endereços
python servidor_visao.py --host 127.0.0.1 --porta 8765 --sem-telemetria
```

| Rota | Resposta |
|---|---|
| `GET /api/snapshot[?experimento=NOME]` | o snapshot (gzip se o cliente aceitar; `no-store`) |
| `GET /api/foto/<nome>.jpg` | foto de `imagens_analisadas/` (nome validado; nada fora da pasta) |
| `GET /`, `/assets/...` | a visão compilada (`web/dist`); sem build, uma página explicando |
| qualquer outro método | `405` (só `GET`/`HEAD`) |

Um snapshot por `VISAO_CACHE_S` (1 s) para todos os clientes juntos. Medido
com a campanha inteira: primeira resposta ~130 ms, depois <1 ms, ~19 KB com
gzip. Não escreve nada em disco (há teste para isso). No Pi:
`./deploy/install.sh --visao` (ver `deploy/README.md`).

## A tela (`web/`)

![modo lavoura, vista de trabalho](screenshots/gemeo-lavoura-trabalho.png)
![modo lavoura, campo todo](screenshots/gemeo-lavoura-campo.png)
![vista da FAPA](screenshots/gemeo-lavoura-fapa.png)

*(capturas da campanha sintética de demonstração, não de dados reais)*

- **Cena:** o campo em escala real, a partir da planilha, no meio do entorno
  da FAPA (OpenStreetMap). Uma estaca com plaquinha na cabeceira de cada plot
  (clicada, seleciona o plot) e um risco claro em volta do ensaio.
- **Três modos** (`?modo=lavoura|emergencia|estado`):
  - *Lavoura* (padrão): solo preparado com camalhão; o ensaio "verdeja"
    conforme o rover analisa. **De perto**, cada carreira analisada mostra as
    plântulas contadas: a quantidade é exata e as falhas são as sementes que
    não emergiram (posição ilustrativa). **De longe** (mais de ~80 m, como o
    "Campo todo"), cada carreira vira um ladrilho na rampa oliva → verde da
    emergência; uma planta ali teria menos de um pixel e as carreiras virariam
    listras.
  - *Emergência*: barras na rampa azul de 6 faixas (para análise fina).
  - *Estado*: neutro como o painel (roxo = capturando).
- **Alerta é forma, não só cor:** moldura âmbar/vermelha em volta do plot
  (no carreador, nunca encostada no ladrilho), bandeirinha na cabeceira da
  carreira que disparou (de perto) e pino (de longe). No modo Lavoura as
  falhas que causaram o alerta continuam visíveis dentro da moldura.
- **Cores validadas** (`validate_palette`): a rampa da Lavoura é um tom só
  (35°), com passos de luminosidade ≥ 0,06 e a ponta escura a 2,28:1 do solo.
  Âmbar e vermelho se confundem com o meio dela para daltônicos, e é por isso
  que o alerta é forma.
- **Vida:** o rover anda na carreira em posição estimada, manobra em U nas
  cabeceiras e as plântulas brotam atrás dele; o vento passa pela lavoura em
  rajadas (shader). Carros na PR-540, sombras de nuvem e aves são cenário.
- **De muito longe** (vista da FAPA): o nome do ensaio e um marcador do rover.
  As lavouras vizinhas são apagadas de propósito, para nenhuma quadra parecer
  mais "ensaio" que o ensaio.
- **Câmera:** abre numa vista de trabalho oblíqua em volta do rover; "Campo
  todo" olha mais de cima; "Ver a FAPA" mostra o entorno. Dado novo nunca mexe
  na câmera.
- **Painel lateral:** rover (posição, última foto, sistema, alertas), plot
  (tabela das 3 carreiras) ou carreira (linhagem com horários gravados).
  A lista de plots em alerta é a "tabela" acessível do mapa.
- **Honestidade:** selo "ao vivo" só com resposta recente; "sem conexão" mostra
  há quanto tempo; DEMONSTRAÇÃO sempre visível com dado sintético; a nota sobre
  o que a contagem significa fica no rodapé do painel.
- **Desempenho:** plantas com 6 triângulos, uma malha por coluna de plots
  (o que sai do quadro é descartado) e refeita só na coluna que mudou. Com o
  ensaio quase todo analisado (~50 mil plantas), 40 a 60 fps numa Intel Iris
  Xe (Chromium, 1800 x 1100). Falta medir num tablet.

Como rodar: `web/README.md`. Demonstração completa sem o rover:
`./ferramentas/rodar_demo.sh` (campanha sintética ao vivo + servidor).

## Limitações conhecidas

- **Contagem = soma das fotos.** Fotos sobrepostas podem contar a mesma planta
  duas vezes; a correção P/R é fixa. É o RV-08 (calibração de campo) que dá
  base ao número absoluto. O limiar de emergência máxima existe para expor
  isso.
- **Relógio do Pi.** As idades são calculadas com o relógio do próprio Pi, então
  são coerentes entre si. Já os horários absolutos dependem de o Pi estar com a
  hora certa (sem rede e sem bateria no RTC, ele pode voltar no tempo após um
  boot).
- **Leitura incremental** não suporta quebra de linha dentro de um campo do CSV
  (o painel não gera isso).
- **Servidor sem senha** nesta versão: qualquer aparelho na mesma rede vê
  contagens e fotos. Para restringir: `ROVER_VISAO_HOST=127.0.0.1`.

## Roadmap

| PR | Entrega | Situação |
|---|---|---|
| `feat/campo-snapshot` | `core/campo.py` + testes + CLI | feito |
| `feat/servidor-visao` | servidor HTTP só leitura + `deploy/visao.service` | feito |
| `feat/web-gemeo-v0` | cena 3D: grade, rover, clique → painel; modo DEMO | feito |
| `feat/web-gemeo-vida` | cena viva: rover estimado, plântulas, efeitos, dia/noite, entorno da FAPA | feito |
| `feat/web-gemeo-lavoura` | modo Lavoura (plantas de perto, ladrilhos de longe), alerta como forma, estacas, cenário apagado | feito |
| `feat/web-gemeo-v1` | replay, tira de fotos | a fazer |
| `feat/exportar-gemeo` | HTML autossuficiente (escritório, estande) | a fazer |
| depois | caixas do YOLO em arquivo à parte, incerteza do RV-08, encoder na roda | conforme o campo |
