# web/: visão 3D do ensaio (gêmeo digital)

Tela só de leitura do campo experimental: plots da planilha, as 3 carreiras de
cada um, o rover e a contagem. Lê o snapshot do `core/campo.py` servido pelo
`servidor_visao.py`. Regras e schema em [`../docs/GEMEO-3D.md`](../docs/GEMEO-3D.md).

Stack: React 19 + TypeScript + Vite, React Three Fiber + drei (cena), zustand
(estado). Tudo empacotado localmente: no campo não há CDN.

## Compilar (máquina de desenvolvimento, não o Pi)

```bash
cd web
corepack pnpm install        # corepack vem com o Node; não precisa instalar npm
corepack pnpm build          # checa tipos e gera web/dist/
```

O Pi só recebe o `web/dist/` pronto (copiar a pasta para `raimunda/web/dist/`);
não precisa de Node lá. O `servidor_visao.py` serve essa pasta.

## Ver funcionando sem o rover

```bash
./ferramentas/rodar_demo.sh                           # da raiz do repo; abre em http://127.0.0.1:8765
ROVER_DEMO_HOST=0.0.0.0 ./ferramentas/rodar_demo.sh   # idem, e abre também de um celular/tablet na rede
```

Sobe uma campanha **sintética** gravando ao vivo (uma foto a cada 0,9 s) em
`~/.cache/rover-demo` e o servidor. A tela mostra a faixa "DEMONSTRAÇÃO". Na
demo não há fotos nem telemetria (o rover é simulado; a máquina que roda a
demo não é o Pi), e o painel diz isso em vez de mostrar números desta máquina.

Sem nem o Python: `corepack pnpm dev` e abra `http://localhost:5173/?demo`,
que lê a foto estática `public/demo/snapshot.json` (gerada por
`corepack pnpm demo`).

## Desenvolver contra o rover (ou a demo)

`corepack pnpm dev` encaminha `/api` para `http://127.0.0.1:8765`
(`VISAO_API=http://<pi>.local:8080 corepack pnpm dev` para o Pi de verdade).

## Parâmetros de URL

| Parâmetro | Efeito |
|---|---|
| `?demo` | usa `demo/snapshot.json` (estático), nunca o servidor |
| `?modo=emergencia` ou `?modo=estado` | abre em outro modo (o padrão é a Lavoura) |
| `?vista=campo` ou `?vista=fapa` | abre no campo todo ou no entorno (ex.: TV de apresentação) |

## Organização

| Arquivo | Papel |
|---|---|
| `src/tipos.ts` | tipos do snapshot (espelho do `core/campo.py`, schema 1) |
| `src/api.ts` | consulta a cada 2 s; modo demo só com `?demo` |
| `src/store.ts` | estado (zustand): snapshot, conexão, seleção, modo de cor, pedidos de câmera |
| `src/cores.ts` | tokens do painel (`ui/tema.py`), rampas da emergência e da lavoura, validadas |
| `src/geometria.ts` | plano do campo → cena (v ao longo das carreiras = eixo X) |
| `src/cena/` | `Campo3D` (solo, plots, carreiras, estacas, alertas), `Lavoura` (plantas e ladrilhos), `Plantulas` (as que brotam), `Rover`, `Ensaio`, `Entorno`, `Vida`, `Rotulos`, `Camera` |
| `src/cena/lod.ts` | nível de detalhe pela distância da câmera (plantas ↔ ladrilhos, marcadores) |
| `src/ui/` | barra do topo, indicadores, painel lateral, legenda e linha do tempo |

Cores: roxo (`#a68cf5`) só para a carreira em captura; âmbar/vermelho só para
alerta, e alerta sempre com forma (moldura, bandeirinha, pino) e texto, nunca
só cor. A rampa da emergência (6 tons de azul) foi validada contra o fundo
`#1a1a1a`; a da lavoura (oliva → verde, um tom só) contra o solo `#45372a`.
