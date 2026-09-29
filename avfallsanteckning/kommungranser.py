import json
import re
from importlib import resources

_TAL = re.compile(r"-?\d+[.,]\d+")


def tolka_koordinat(text):
    tal = [float(t.replace(",", ".")) for t in _TAL.findall(text or "")]
    if len(tal) != 2:
        return None
    a, b = tal
    if 54 <= a <= 70 and 10 <= b <= 25:
        return a, b
    if 54 <= b <= 70 and 10 <= a <= 25:
        return b, a
    return None


def _inuti(ringar, lat, lon):
    # jämn-udda-regeln över alla ringar, så hål räknas bort av sig själva
    inne = False
    for ring in ringar:
        j = len(ring) - 1
        for i in range(len(ring)):
            (xi, yi), (xj, yj) = ring[i], ring[j]
            if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                inne = not inne
            j = i
    return inne


class Kommungranser:
    def __init__(self, kommuner):
        self.kommuner = kommuner

    @classmethod
    def load(cls):
        fil = resources.files(__package__).joinpath("data/kommungranser.json")
        with fil.open(encoding="utf-8") as f:
            return cls(json.load(f))

    def kod(self, text):
        punkt = tolka_koordinat(text)
        if not punkt:
            return None
        lat, lon = punkt
        for k in self.kommuner:
            v, s, o, n = k["bbox"]
            if v <= lon <= o and s <= lat <= n and _inuti(k["ringar"], lat, lon):
                return k["kod"]
        return None
