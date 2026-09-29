"""Bygger avfallsanteckning/data/kommungranser.json ur SCB:s digitala kommungränser.

Kör utan argument för att hämta zip-filen, eller ange en sparad zip. Behöver pyshp och pyproj.
Gränserna är SCB:s förenklade (för tematiska kartor, inte för exakt gränsdragning) och
tunnas ut ytterligare här; fel nära en gräns är därför möjliga och fältet går alltid att ändra.
"""

import io
import json
import sys
import urllib.request
import zipfile
from itertools import pairwise
from pathlib import Path

import shapefile
from pyproj import Transformer

URL = "https://www.scb.se/contentassets/3443fea3fa6640f7a57ea15d9a372d33/shape_svenska_260225.zip"
UT = Path(__file__).resolve().parent.parent / "avfallsanteckning" / "data" / "kommungranser.json"
TOLERANS = 40  # meter, i SWEREF99 TM före omräkningen


def _avstand(p, a, b):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == dy == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
    return ((x - x1 - t * dx) ** 2 + (y - y1 - t * dy) ** 2) ** 0.5


def tunna(ring, tolerans):
    # Douglas–Peucker, iterativt
    behall = [False] * len(ring)
    behall[0] = behall[-1] = True
    stack = [(0, len(ring) - 1)]
    while stack:
        i, j = stack.pop()
        if j - i < 2:
            continue
        k, storst = -1, tolerans
        for m in range(i + 1, j):
            d = _avstand(ring[m], ring[i], ring[j])
            if d > storst:
                k, storst = m, d
        if k >= 0:
            behall[k] = True
            stack += [(i, k), (k, j)]
    return [p for p, b in zip(ring, behall) if b]


def las(zipdata):
    z = zipfile.ZipFile(io.BytesIO(zipdata))
    # scb:s zip innehåller en zip per indelning
    inre = next((n for n in z.namelist() if n.lower().endswith(".zip") and "kommun" in n.lower()), None)
    if inre:
        z = zipfile.ZipFile(io.BytesIO(z.read(inre)))
    namn = next(n[:-4] for n in z.namelist() if n.lower().endswith(".shp"))
    sf = shapefile.Reader(
        shp=io.BytesIO(z.read(namn + ".shp")),
        dbf=io.BytesIO(z.read(namn + ".dbf")),
        shx=io.BytesIO(z.read(namn + ".shx")),
        encoding="latin-1",
    )
    falt = [f[0] for f in sf.fields[1:]]
    kodfalt = next(f for f in falt if "kod" in f.lower())
    namnfalt = next(f for f in falt if "namn" in f.lower())
    return sf, falt.index(kodfalt), falt.index(namnfalt)


def bygg(zipdata):
    sf, ikod, inamn = las(zipdata)
    till_wgs = Transformer.from_crs("EPSG:3006", "EPSG:4326", always_xy=True)
    kommuner = []
    for rad in sf.iterShapeRecords():
        punkter = rad.shape.points
        delar = [*rad.shape.parts, len(punkter)]
        ringar = []
        for a, b in pairwise(delar):
            ring = tunna(punkter[a:b], TOLERANS)
            if len(ring) < 4:
                continue
            lon, lat = till_wgs.transform([p[0] for p in ring], [p[1] for p in ring])
            ringar.append([[round(x, 5), round(y, 5)] for x, y in zip(lon, lat)])
        alla = [p for r in ringar for p in r]
        bbox = [min(p[0] for p in alla), min(p[1] for p in alla), max(p[0] for p in alla), max(p[1] for p in alla)]
        kommuner.append({"kod": rad.record[ikod], "namn": rad.record[inamn], "bbox": bbox, "ringar": ringar})
    kommuner.sort(key=lambda k: k["kod"])
    return kommuner


def main():
    if len(sys.argv) > 1:
        zipdata = Path(sys.argv[1]).read_bytes()
    else:
        with urllib.request.urlopen(URL) as svar:
            zipdata = svar.read()
    kommuner = bygg(zipdata)
    UT.write_text(json.dumps(kommuner, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    hörn = sum(len(r) for k in kommuner for r in k["ringar"])
    print(f"{len(kommuner)} kommuner, {hörn} hörn, {UT.stat().st_size // 1024} kB → {UT}")


if __name__ == "__main__":
    main()
