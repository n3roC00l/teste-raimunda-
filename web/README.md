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
./ferramentas/rodar_demo.sh                    # da raiz do repo; abre em http://127.0.0.1:8765
```

Sobe uma campanha **sintética** gravando ao vivo (uma foto a cada 0,9 s) numa
pasta temporária e o servidor. A tela mostra a faixa "DEMONSTRAÇÃO".

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
| `?modo=emergencia` | abre já no mapa de emergência (ex.: tela de apresentação) |

## Organização

| Arquivo | Papel |
|---|---|
| `src/tipos.ts` | tipos do snapshot (espelho do `core/campo.py`, schema 1) |
| `src/api.ts` | consulta a cada 2 s; modo demo só com `?demo` |
| `src/store.ts` | estado (zustand): snapshot, conexão, seleção, modo de cor, pedidos de câmera |
| `src/cores.ts` | tokens do painel (`ui/tema.py`) e a rampa da emergência, validados |
| `src/geometria.ts` | plano do campo → cena (v ao longo das carreiras = eixo X) |
| `src/cena/` | `Campo3D` (chão, plots, carreiras, pinos), `Rover`, `Rotulos`, `Camera` |
| `src/ui/` | barra do topo, indicadores, painel lateral, legenda e linha do tempo |

Cores: neutro por padrão; roxo (`#a68cf5`) só para a carreira em captura;
âmbar/vermelho só para alerta, e alerta sempre com pino 3D e texto (nunca só
cor). A rampa da emergência (6 tons de azul) foi validada para daltonismo e
contraste contra o fundo `#1a1a1a`.
