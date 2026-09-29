import re

from . import db, orgnr

STANDARD = {
    "verksamhet": {
        "namn": "",
        "orgnr": "",
        "adress": "",
        "postnummer": "",
        "ort": "",
        "cfar": "",
        "kontakt": "",
    },
    "favoriter": {"koder": []},
    "transportor": {"aktiv": False, "blankett_beskrivning": "", "blankett_producent": "", "bedomningsgrunder": []},
}

ARBETSSTALLE = {"namn": "", "adress": "", "kommun": "", "cfar": ""}


def las(conn, kommuner):
    sparat = db.installningar(conn)
    inst = {namn: {**standard, **sparat.get(namn, {})} for namn, standard in STANDARD.items()}
    v = inst["verksamhet"]
    v["postort"] = f"{v['postnummer']} {v['ort']}".strip()
    v["adressrad"] = ", ".join(x for x in (v["adress"], v["postort"]) if x)
    stallen = [{**ARBETSSTALLE, **s} for s in sparat.get("arbetsstallen", [])]
    inst["egna_stallen"] = bool(stallen)
    if not stallen:
        # postorten är oftast också kommunen; annars får platsen ingen kommun
        kommun = v["ort"] if kommuner.kod(v["ort"]) else ""
        eget = {"namn": v["namn"], "adress": v["adressrad"], "kommun": kommun, "cfar": v["cfar"]}
        stallen = [{**ARBETSSTALLE, **eget}]
    for s in stallen:
        s["kommunkod"] = kommuner.kod(s["kommun"]) or ""
        s["kommun"] = kommuner.namn(s["kommunkod"]) or s["kommun"]
    inst["arbetsstallen"] = stallen
    inst["saknas"] = not v["namn"]
    return inst


def tolka(form, kommuner, koder):
    fel = []
    v = {k: form.get(k, "").strip() for k in STANDARD["verksamhet"]}
    if not v["namn"]:
        fel.append("Ange verksamhetens namn.")
    if v["orgnr"] and not orgnr.giltigt(v["orgnr"]):
        fel.append(f"Ogiltigt org.nr: {v['orgnr']}.")
    elif v["orgnr"]:
        v["orgnr"] = orgnr.formatera(v["orgnr"])
    favoriter = []
    for text in re.split(r"[,;\n]", form.get("koder", "")):
        if not text.strip():
            continue
        kod = koder.get(text)
        if not kod:
            fel.append(f"Okänd avfallskod: {text.strip()}.")
        elif kod["kod"] not in favoriter:
            favoriter.append(kod["kod"])
    t = {
        "aktiv": bool(form.get("aktiv")),
        "blankett_beskrivning": form.get("blankett_beskrivning", "").strip(),
        "blankett_producent": form.get("blankett_producent", "").strip(),
        "bedomningsgrunder": [r.strip() for r in form.get("bedomningsgrunder", "").splitlines() if r.strip()],
    }
    stallen = []
    for varden in zip(*(form.getlist(f"stalle_{f}") for f in ARBETSSTALLE)):
        s = dict(zip(ARBETSSTALLE, (x.strip() for x in varden)))
        if not any(s.values()):
            continue
        if not s["namn"]:
            fel.append("Ange namn på arbetsstället.")
        if s["kommun"] and not kommuner.kod(s["kommun"]):
            fel.append(f"Okänd kommun: {s['kommun']}.")
        stallen.append(s)
    data = {"verksamhet": v, "favoriter": {"koder": favoriter}, "transportor": t, "arbetsstallen": stallen}
    return data, fel
