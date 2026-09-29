"""Bygger avfallsanteckning/data/avfallskoder.json ur bilaga 3 till avfallsförordningen (2020:614).

Källa: riksdagens öppna data. Kör utan argument för att hämta texten, eller ange en sparad textfil.
Ändrade avsnitt står med två lydelser: "/Upphör att gälla U:ÅÅÅÅ-MM-DD/" inleder den gamla och
"/Träder i kraft I:ÅÅÅÅ-MM-DD/" den nya, som slutar där texten passerar den gamla lydelsens sista
kod. Båda sparas med giltighetsdatum så att appen byter lydelse av sig själv.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

URL = "https://data.riksdagen.se/dokument/sfs-2020-614.text"
UT = Path(__file__).resolve().parent.parent / "avfallsanteckning" / "data" / "avfallskoder.json"

KOD = re.compile(r"^(\d{2} \d{2} \d{2}\*?) (\S.*)$")
UNDERKAPITEL = re.compile(r"^(\d{2} \d{2}) (\D.*)$")
KAPITEL = re.compile(r"^(\d{2}) (\D.*)$")
NYCKEL = re.compile(r"^(\d{2})(?: (\d{2}))?(?: (\d{2}))?\*? \D")
UPPHOR = re.compile(r"^/Upphör att gälla U:(\d{4}-\d{2}-\d{2})/$")
IKRAFT = re.compile(r"^/Träder i kraft I:(\d{4}-\d{2}-\d{2})/$")
FORORDNING = re.compile(r"\s*Förordning \(\d{4}:\d+\)\.?$")


def stycken(text):
    start = text.index("\nBilaga 3\n")
    slut = text.index("\nBilaga 4\n", start)
    rader = []

    def stycke():
        rad = " ".join(r.strip() for r in rader)
        rader.clear()
        return re.sub(r"(\d)- (\d)", r"\1-\2", FORORDNING.sub("", rad)).strip()

    # markeringarna kan stå mitt i ett stycke
    for rad in [*text[start:slut].splitlines(), ""]:
        u, i = UPPHOR.match(rad.strip()), IKRAFT.match(rad.strip())
        if u or i or not rad.strip():
            if klar := stycke():
                yield ("rad", klar)
            if u:
                yield ("upphor", u[1])
            if i:
                yield ("ikraft", i[1])
        else:
            rader.append(rad)


def nyckel(rad):
    m = NYCKEL.match(rad)
    return tuple(int(x or 0) for x in m.groups()) if m else None


def tolka(text):
    koder, kapitel, underkapitel = [], None, None
    lage, datum, gammal_max = "nu", None, None
    for slag, rad in stycken(text):
        if slag == "upphor":
            lage, datum, gammal_max = "gammal", rad, (0, 0, 0)
            continue
        if slag == "ikraft":
            lage, datum = "ny", rad
            continue
        k = nyckel(rad)
        if k is None:
            continue
        if lage == "gammal":
            gammal_max = max(gammal_max, k)
        elif lage == "ny" and k[2] == 0 and k > gammal_max:
            # nästa rubrik efter det ersatta avsnittet: nuvarande lydelse fortsätter
            lage = "nu"
        m = KOD.match(rad)
        if m:
            koder.append(
                {
                    "kod": m[1],
                    "farligt": m[1].endswith("*"),
                    "beskrivning": m[2].rstrip("."),
                    "kapitel": kapitel[0],
                    "kapitelnamn": kapitel[1],
                    "underkapitel": underkapitel[0],
                    "underkapitelnamn": underkapitel[1],
                    "fran": datum if lage == "ny" else None,
                    "till": datum if lage == "gammal" else None,
                }
            )
            continue
        m = UNDERKAPITEL.match(rad)
        if m:
            underkapitel = (m[1], m[2].rstrip(":"))
            continue
        m = KAPITEL.match(rad)
        if m:
            kapitel = (m[1], m[2].strip())
    return koder


def main(argv):
    if len(argv) > 1:
        text = Path(argv[1]).read_text(encoding="utf-8")
    else:
        with urllib.request.urlopen(URL, timeout=30) as svar:
            text = svar.read().decode("utf-8")
    koder = tolka(text)
    nuvarande = [k for k in koder if k["fran"] is None]
    if len(nuvarande) < 800 or len({k["kod"] for k in nuvarande}) != len(nuvarande):
        raise SystemExit(f"oväntat resultat: {len(nuvarande)} koder i nuvarande lydelse")
    UT.write_text(json.dumps(koder, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    kommande = len(koder) - len(nuvarande)
    farliga = sum(k["farligt"] for k in nuvarande)
    print(f"{len(nuvarande)} koder ({farliga} farliga) och {kommande} i kommande lydelse skrivna till {UT}")


if __name__ == "__main__":
    main(sys.argv)
