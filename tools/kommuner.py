"""Bygger avfallsanteckning/data/kommuner.json ur SCB:s lista över kommuner i kodnummerordning.

Kör utan argument för att hämta sidan, eller ange en sparad HTML-fil.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

URL = (
    "https://www.scb.se/hitta-statistik/regional-statistik-och-kartor/regionala-indelningar/"
    "lan-och-kommuner/lan-och-kommuner-i-kodnummerordning/"
)
UT = Path(__file__).resolve().parent.parent / "avfallsanteckning" / "data" / "kommuner.json"
KOMMUN = re.compile(r"^(\d{4}) (\S.*?)\s*$")


def tolka(html):
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"<[^>]+>", "\n", text).replace("&amp;", "&")
    kommuner = []
    for rad in text.splitlines():
        m = KOMMUN.match(rad.strip())
        if m:
            kommuner.append({"kod": m[1], "namn": m[2]})
    return kommuner


def main(argv):
    if len(argv) > 1:
        html = Path(argv[1]).read_text(encoding="utf-8")
    else:
        begaran = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(begaran, timeout=30) as svar:
            html = svar.read().decode("utf-8")
    kommuner = tolka(html)
    if len(kommuner) != 290 or len({k["kod"] for k in kommuner}) != 290:
        raise SystemExit(f"oväntat resultat: {len(kommuner)} kommuner")
    UT.write_text(json.dumps(kommuner, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print(f"{len(kommuner)} kommuner skrivna till {UT}")


if __name__ == "__main__":
    main(sys.argv)
