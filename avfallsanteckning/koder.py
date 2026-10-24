import json
import re
from importlib import resources

from .tid import idag

_EJ_SIFFRA = re.compile(r"\D")


def normalisera(kod):
    kod = (kod or "").strip()
    siffror = _EJ_SIFFRA.sub("", kod)
    if len(siffror) != 6:
        return None
    return f"{siffror[:2]} {siffror[2:4]} {siffror[4:]}" + ("*" if kod.endswith("*") else "")


def gallande(alla, datum):
    d = datum.isoformat()
    return [k for k in alla if (k["fran"] is None or k["fran"] <= d) and (k["till"] is None or d < k["till"])]


class Koder:
    def __init__(self, alla, datum=None):
        self.alla = alla
        # utan datum följer listan dagens datum, så en ny lydelse gäller från sin dag utan omstart
        self.datum = datum
        self._dag = None

    @classmethod
    def load(cls, datum=None):
        fil = resources.files(__package__).joinpath("data/avfallskoder.json")
        with fil.open(encoding="utf-8") as f:
            return cls(json.load(f), datum)

    def _galler(self):
        dag = self.datum or idag()
        if dag != self._dag:
            lista = gallande(self.alla, dag)
            self._lista, self._per_kod, self._dag = lista, {k["kod"]: k for k in lista}, dag
        return self._lista, self._per_kod

    @property
    def lista(self):
        return self._galler()[0]

    def get(self, kod):
        n = normalisera(kod)
        return self._galler()[1].get(n) if n else None
