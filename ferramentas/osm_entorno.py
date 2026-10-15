"""
ferramentas/osm_entorno.py: gera o entorno da FAPA para a visão 3D a partir
do OpenStreetMap (estradas, riachos, matas, água, prédios mapeados).

    python ferramentas/osm_entorno.py                       # baixa do Overpass
    python ferramentas/osm_entorno.py --entrada bruto.json  # usa um download salvo

Saída: web/public/entorno/fapa.json (lat/lon; a tela projeta no plano do
campo usando campo.geo do snapshot). Roda na máquina de desenvolvimento, uma
vez; o Pi recebe o arquivo pronto dentro do web/dist (no campo não há internet).

Licença dos dados: © colaboradores do OpenStreetMap, ODbL. A atribuição vai
no próprio arquivo e aparece na tela.

Os prédios da FAPA e do Centro de Eventos NÃO estão no OSM: entram aqui
desenhados à mão, com posição e tamanho APROXIMADOS (marcados "aproximado").
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from datetime import date

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import config

SAIDA_PADRAO = os.path.join(RAIZ, "web", "public", "entorno", "fapa.json")
OVERPASS = "https://overpass-api.de/api/interpreter"
ATRIBUICAO = "© colaboradores do OpenStreetMap (ODbL) · openstreetmap.org/copyright"

# largura visual (m) por tipo de via
LARGURA = {"motorway": 12, "trunk": 11, "primary": 10, "secondary": 9, "secondary_link": 6,
           "tertiary": 7, "unclassified": 6, "residential": 6, "service": 4, "track": 3}
AREAS = {("landuse", "forest"): "mata", ("natural", "wood"): "mata", ("natural", "scrub"): "mata",
         ("natural", "water"): "agua", ("landuse", "reservoir"): "agua", ("landuse", "farmyard"): "sede_rural",
         ("leisure", "park"): "gramado", ("leisure", "pitch"): "gramado", ("landuse", "grass"): "gramado",
         ("landuse", "meadow"): "gramado", ("landuse", "cemetery"): "gramado"}

# Prédios desenhados à mão (não estão no OSM). Centro aproximado lido da vista
# de satélite + plus code da FAPA (FG36+2P), rumo do campus ~70°.
PREDIOS_APROXIMADOS = [
    # nome, lat, lon, comprimento (m, no rumo), largura (m), altura (m), tipo
    ("Sede FAPA", -25.54744, -51.48844, 46, 16, 8, "predio"),
    ("Laboratórios FAPA", -25.54700, -51.48905, 36, 14, 6, "predio"),
    ("Galpão de máquinas", -25.54790, -51.48770, 40, 18, 7, "galpao"),
    ("Galpão de sementes", -25.54818, -51.48800, 30, 14, 6, "galpao"),
    ("Casa de vegetação", -25.54668, -51.48838, 24, 8, 4, "estufa"),
    ("Casa de vegetação", -25.54655, -51.48820, 24, 8, 4, "estufa"),
    ("Centro de Eventos Agrária", -25.54811, -51.49234, 60, 38, 12, "predio"),
]
RUMO_CAMPUS = 70.0


def _metros(lat0):
    """Metros por grau (lat, lon) perto de lat0 (aproximação equiretangular)."""
    return 110540.0, 111320.0 * math.cos(math.radians(lat0))


def _distancia_m(a, b):
    mlat, mlon = _metros(a[0])
    return math.hypot((a[0] - b[0]) * mlat, (a[1] - b[1]) * mlon)


def _simplificar(pontos, tolerancia_m=1.0):
    """Douglas-Peucker em metros (pontos = [[lat, lon], ...])."""
    if len(pontos) < 3:
        return pontos
    mlat, mlon = _metros(pontos[0][0])
    xy = [((p[1] - pontos[0][1]) * mlon, (p[0] - pontos[0][0]) * mlat) for p in pontos]

    def dist(p, a, b):
        (x, y), (x1, y1), (x2, y2) = p, a, b
        dx, dy = x2 - x1, y2 - y1
        if dx == dy == 0:
            return math.hypot(x - x1, y - y1)
        t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))

    manter = [False] * len(xy)
    manter[0] = manter[-1] = True
    pilha = [(0, len(xy) - 1)]
    while pilha:
        i, j = pilha.pop()
        k, dmax = None, tolerancia_m
        for n in range(i + 1, j):
            d = dist(xy[n], xy[i], xy[j])
            if d > dmax:
                k, dmax = n, d
        if k is not None:
            manter[k] = True
            pilha += [(i, k), (k, j)]
    return [p for p, m in zip(pontos, manter) if m]


def _retangulo(lat, lon, comprimento, largura, rumo_graus):
    """Cantos (lat, lon) de um retângulo centrado em (lat, lon), girado no rumo."""
    mlat, mlon = _metros(lat)
    r = math.radians(rumo_graus)
    ao_longo = (math.sin(r), math.cos(r))               # (leste, norte)
    atraves = (math.sin(r + math.pi / 2), math.cos(r + math.pi / 2))
    cantos = []
    for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        e = a * comprimento / 2 * ao_longo[0] + b * largura / 2 * atraves[0]
        n = a * comprimento / 2 * ao_longo[1] + b * largura / 2 * atraves[1]
        cantos.append([round(lat + n / mlat, 7), round(lon + e / mlon, 7)])
    return cantos


def _baixar(centro, raio_m):
    mlat, mlon = _metros(centro[0])
    dlat, dlon = raio_m / mlat, raio_m / mlon
    bbox = f"{centro[0] - dlat:.5f},{centro[1] - dlon:.5f},{centro[0] + dlat:.5f},{centro[1] + dlon:.5f}"
    consulta = f"""[out:json][timeout:90];
(
  way["highway"]({bbox}); way["building"]({bbox});
  way["landuse"]({bbox}); way["natural"]({bbox});
  way["waterway"]({bbox}); way["leisure"]({bbox});
  node["name"]({bbox});
);
out geom tags;"""
    pedido = urllib.request.Request(
        OVERPASS, data=urllib.parse.urlencode({"data": consulta}).encode(),
        headers={"User-Agent": "raimunda-gemeo/0.1 (visão 3D de ensaio agrícola)"})
    with urllib.request.urlopen(pedido, timeout=120) as r:
        return json.load(r)


def converter(bruto, centro, raio_m):
    """Overpass JSON -> entorno simplificado (só o que está até raio_m do centro)."""
    perto = lambda pts: any(_distancia_m(p, centro) <= raio_m for p in pts)
    saida = {"fonte": ATRIBUICAO, "obtido_em": date.today().isoformat(),
             "centro": list(centro), "raio_m": raio_m,
             "estradas": [], "rios": [], "areas": [], "predios": [], "marcos": []}
    for e in bruto.get("elements", []):
        t = e.get("tags", {})
        if e["type"] == "node":
            if t.get("name") and _distancia_m((e["lat"], e["lon"]), centro) <= raio_m:
                saida["marcos"].append({"nome": t["name"], "lat": e["lat"], "lon": e["lon"]})
            continue
        pts = [[round(p["lat"], 7), round(p["lon"], 7)] for p in e.get("geometry") or []]
        if len(pts) < 2 or not perto(pts):
            continue
        fechado = pts[0] == pts[-1] and len(pts) >= 4
        via = t.get("highway")
        if via in LARGURA:
            saida["estradas"].append({"tipo": via, "nome": t.get("name", ""), "ref": t.get("ref", ""),
                                      "largura_m": LARGURA[via], "pontos": _simplificar(pts)})
        elif t.get("waterway") in ("stream", "river", "canal", "ditch"):
            saida["rios"].append({"nome": t.get("name", ""),
                                  "largura_m": 6 if t["waterway"] == "river" else 1.5,
                                  "pontos": _simplificar(pts)})
        elif "building" in t and fechado:
            andares = t.get("building:levels")
            altura = float(andares) * 3 if (andares or "").replace(".", "", 1).isdigit() else 6
            saida["predios"].append({"nome": t.get("name", ""), "tipo": "predio", "altura_m": altura,
                                     "aproximado": False, "pontos": pts[:-1]})
        elif fechado:
            for (chave, valor), tipo in AREAS.items():
                if t.get(chave) == valor:
                    saida["areas"].append({"tipo": tipo, "nome": t.get("name", ""),
                                           "pontos": _simplificar(pts)[:-1]})
                    break
    for nome, lat, lon, comp, larg, alt, tipo in PREDIOS_APROXIMADOS:
        saida["predios"].append({"nome": nome, "tipo": tipo, "altura_m": alt, "aproximado": True,
                                 "pontos": _retangulo(lat, lon, comp, larg, RUMO_CAMPUS)})
    saida["marcos"] += [
        {"nome": "FAPA", "lat": -25.54744, "lon": -51.48844},
        {"nome": "Centro de Eventos Agrária", "lat": -25.54811, "lon": -51.49234},
    ]
    return saida


def main(argv=None):
    ap = argparse.ArgumentParser(description="Entorno da FAPA (OpenStreetMap) para a visão 3D.")
    ap.add_argument("--entrada", help="JSON do Overpass já baixado (senão, baixa)")
    ap.add_argument("--saida", default=SAIDA_PADRAO)
    ap.add_argument("--raio-m", type=float, default=900)
    args = ap.parse_args(argv)
    centro = (config.CAMPO_GEO_LAT, config.CAMPO_GEO_LON)
    if args.entrada:
        with open(args.entrada, encoding="utf-8") as f:
            bruto = json.load(f)
    else:
        bruto = _baixar(centro, args.raio_m)
    saida = converter(bruto, centro, args.raio_m)
    os.makedirs(os.path.dirname(os.path.abspath(args.saida)), exist_ok=True)
    with open(args.saida, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, separators=(",", ":"))
    print(f"ENTORNO: {args.saida}: {len(saida['estradas'])} vias, {len(saida['rios'])} cursos d'água, "
          f"{len(saida['areas'])} áreas, {len(saida['predios'])} prédios, {len(saida['marcos'])} marcos")


if __name__ == "__main__":
    main()
