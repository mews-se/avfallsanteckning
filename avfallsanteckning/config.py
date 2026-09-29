import os
import tomllib

STANDARD = {
    "verksamhet": {
        "namn": "",
        "orgnr": "",
        "adress": "",
        "postnummer": "",
        "ort": "",
        "kommun": "",
        "kommunkod": "",
        "cfar": "",
        "kontakt": "",
    },
    "favoriter": {"koder": []},
    "transportor": {"aktiv": False, "blankett_beskrivning": "", "blankett_producent": "", "bedomningsgrunder": []},
}

ARBETSSTALLE = {"namn": "", "adress": "", "kommun": "", "cfar": ""}


def load(path=None):
    path = path or os.environ.get("AVFALLSANTECKNING_CONFIG", "config.toml")
    raw = {}
    if os.path.exists(path):
        with open(path, "rb") as f:
            raw = tomllib.load(f)
    inst = {namn: {**standard, **raw.get(namn, {})} for namn, standard in STANDARD.items()}
    v = inst["verksamhet"]
    v["postort"] = f"{v['postnummer']} {v['ort']}".strip()
    v["adressrad"] = ", ".join(x for x in (v["adress"], v["postort"]) if x)
    stallen = [{**ARBETSSTALLE, **s} for s in raw.get("arbetsstallen", [])]
    if not stallen:
        eget = {"namn": v["namn"], "adress": v["adressrad"], "kommun": v["kommun"], "cfar": v["cfar"]}
        stallen = [{**ARBETSSTALLE, **eget}]
    inst["arbetsstallen"] = stallen
    inst["saknas"] = not os.path.exists(path)
    return inst
