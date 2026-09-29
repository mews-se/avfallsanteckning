import json
import re
from importlib import resources

_KOD = re.compile(r"^\d{4}$")


def normalisera(namn):
    n = " ".join(namn.lower().split())
    n = re.sub(r"s? kommun$", "", n)
    return n


class Kommuner:
    def __init__(self, lista):
        self.lista = lista
        self.per_kod = {k["kod"]: k["namn"] for k in lista}
        self.per_namn = {normalisera(k["namn"]): k["kod"] for k in lista}

    @classmethod
    def load(cls):
        fil = resources.files(__package__).joinpath("data/kommuner.json")
        with fil.open(encoding="utf-8") as f:
            return cls(json.load(f))

    def namn(self, kod):
        return self.per_kod.get(kod or "", "")

    def kod(self, text):
        text = (text or "").strip()
        if not text:
            return ""
        if _KOD.match(text):
            return text if text in self.per_kod else None
        n = normalisera(text)
        # "Stockholms" och "Stockholms kommun" ska träffa Stockholm
        return self.per_namn.get(n) or self.per_namn.get(n.rstrip("s"))
