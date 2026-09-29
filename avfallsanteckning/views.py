import csv
import io
import json
import mimetypes
import secrets
from datetime import date

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from werkzeug.utils import secure_filename

from . import db, pdf
from .arbetsdagar import rapportera_senast
from .texter import GRUND, KLASSGRUND_TEXT, KLASSGRUNDER, ROLL_HJALP, ROLLER, STATUS, TRANSPORTSATT
from .tid import idag, stampel

bp = Blueprint("app", __name__)

BILAGA_TYPER = {"pdf", "jpg", "jpeg", "png", "heic", "webp"}
VECKODAG = ["mån", "tis", "ons", "tor", "fre", "lör", "sön"]
MANAD = ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]
KOPIERAS_EJ = {"avfallskod", "avfallstyp", "farligt", "vikt_kg", "vikt_uppskattad", "notering"}


def get_db():
    if "db" not in g:
        g.db = db.anslut(current_app.config["DB_PATH"])
    return g.db


@bp.teardown_app_request
def _stang(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


@bp.app_context_processor
def _globalt():
    return {
        "inst": current_app.config["INST"],
        "version": current_app.config["VERSION"],
        "ROLLER": ROLLER,
        "STATUS": STATUS,
        "GRUND": GRUND,
        "idag": idag().isoformat(),
    }


@bp.app_template_filter("vikt")
def f_vikt(v):
    s = f"{float(v or 0):,.1f}".replace(",", "\N{NO-BREAK SPACE}").replace(".", ",")
    return s.rstrip("0").rstrip(",")


@bp.app_template_filter("dag")
def f_dag(s):
    if not s:
        return "–"
    d = date.fromisoformat(s)
    return f"{VECKODAG[d.weekday()]} {d.day} {MANAD[d.month - 1]} {d.year}"


@bp.app_template_filter("kommunnamn")
def f_kommunnamn(kod):
    return current_app.config["KOMMUNER"].namn(kod) or (kod or "")


@bp.app_template_filter("kommun")
def f_kommun(kod):
    namn = current_app.config["KOMMUNER"].namn(kod)
    return f"{namn} ({kod})" if namn else (kod or "")


def berika(rad):
    p = dict(rad)
    kommuner = current_app.config["KOMMUNER"]
    p["fran_kommun"] = kommuner.namn(p["fran_kommunkod"])
    p["till_kommun"] = kommuner.namn(p["till_kommunkod"])
    p["klassgrund_lista"] = [KLASSGRUND_TEXT.get(k, k) for k in json.loads(p["klassgrund"] or "[]")]
    p["senast"] = p["dagar_kvar"] = None
    p["forsenad"] = False
    if p["farligt"] and p["status"] != "makulerad":
        senast = rapportera_senast(date.fromisoformat(p["transportdatum"]))
        p["senast"] = senast.isoformat()
        if p["status"] == "antecknad":
            p["dagar_kvar"] = (senast - idag()).days
            p["forsenad"] = p["dagar_kvar"] < 0
    return p


def _oppna(conn):
    return [berika(r) for r in db.lista(conn, status="antecknad") if r["farligt"]]


@bp.get("/")
def index():
    conn = get_db()
    ar = request.args.get("ar") or str(idag().year)
    roll = request.args.get("roll", "")
    status = request.args.get("status", "")
    rader = [
        berika(r)
        for r in db.lista(conn, None if ar == "alla" else ar, roll or None, status or None)
    ]
    oppna = _oppna(conn)
    stat = {
        "antal": len(rader),
        "att_rapportera": len(oppna),
        "forsenade": sum(1 for p in oppna if p["forsenad"]),
    }
    ar_lista = db.ar_lista(conn)
    if ar != "alla" and ar not in ar_lista:
        ar_lista.insert(0, ar)
    return render_template(
        "index.html", rader=rader, ar=ar, roll=roll, status=status, ar_lista=ar_lista, stat=stat
    )


def _formkontext(conn, roll):
    return {
        "transportorer": db.parter(conn, "transportor"),
        "mottagare": db.parter(conn, "mottagare"),
        "TRANSPORTSATT": TRANSPORTSATT,
        "KLASSGRUNDER": KLASSGRUNDER,
        "kommuner": current_app.config["KOMMUNER"].lista,
        "arbetsstallen": current_app.config["INST"]["arbetsstallen"],
        "favoriter": json.dumps(current_app.config["INST"]["favoriter"]["koder"]),
        "hjalp": ROLL_HJALP[roll],
    }


def _standardvarden(roll):
    v = current_app.config["INST"]["verksamhet"]
    varden = {
        "transportdatum": idag().isoformat(),
        "transportsatt": TRANSPORTSATT[0],
        "fran_kommun": v["kommun"],
        "klassgrund": [],
    }
    if roll == "producent":
        s = current_app.config["INST"]["arbetsstallen"][0]
        varden["arbetsstalle"] = "0"
        varden.update(fran_adress=s["adress"], fran_kommun=s["kommun"], fran_cfar=s["cfar"])
    else:
        varden["lamnare_namn"] = "Okänd"
    return varden


def _arbetsstalle(val):
    lista = current_app.config["INST"]["arbetsstallen"]
    return lista[int(val)] if val.isdigit() and int(val) < len(lista) else None


def _arbetsstalleindex(rad):
    for i, s in enumerate(current_app.config["INST"]["arbetsstallen"]):
        if (s["adress"], s["kommunkod"], s["cfar"]) == (rad["fran_adress"], rad["fran_kommunkod"], rad["fran_cfar"]):
            return str(i)
    return ""


def _formvarden(form):
    varden = {k: form.get(k, "") for k in form}
    varden["klassgrund"] = form.getlist("klassgrund")
    return varden


def _radvarden(rad):
    varden = dict(rad)
    varden["klassgrund"] = json.loads(rad["klassgrund"] or "[]")
    varden["vikt_kg"] = f_vikt(rad["vikt_kg"])
    varden["fran_kommun"] = f_kommunnamn(rad["fran_kommunkod"])
    varden["till_kommun"] = f_kommunnamn(rad["till_kommunkod"])
    if rad["roll"] == "producent":
        varden["arbetsstalle"] = _arbetsstalleindex(rad)
    return varden


def _tal(s):
    try:
        return float(s.replace("\N{NO-BREAK SPACE}", "").replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def _datum(s):
    try:
        return date.fromisoformat(s.strip()).isoformat()
    except ValueError:
        return None


def _part(form, prefix, conn):
    pid = form.get(f"{prefix}_id", "")
    if pid.isdigit():
        p = db.part(conn, int(pid))
        if p:
            return p["namn"], p["orgnr"], p["adress"], p["kommunkod"]
    return form.get(f"{prefix}_namn", "").strip(), form.get(f"{prefix}_orgnr", "").strip(), "", ""


def _las_formular(roll, form, conn):
    fel = []
    v = current_app.config["INST"]["verksamhet"]
    kod = current_app.config["KODER"].get(form.get("avfallskod", ""))
    if not kod:
        fel.append("Välj en avfallskod ur listan.")
    vikt = _tal(form.get("vikt_kg", ""))
    if vikt is None or vikt <= 0:
        fel.append("Ange vikt i kilogram, större än 0.")
    datum = _datum(form.get("transportdatum", ""))
    if not datum:
        fel.append("Ange transportdatum.")
    transportsatt = form.get("transportsatt", TRANSPORTSATT[0])
    if transportsatt not in TRANSPORTSATT:
        fel.append("Ogiltigt transportsätt.")
    klassgrund = [k for k in form.getlist("klassgrund") if k in KLASSGRUND_TEXT]
    text = {k: form.get(k, "").strip() for k in db.FALT}
    data = {
        **text,
        "roll": roll,
        "avfallskod": kod["kod"] if kod else "",
        "avfallstyp": kod["beskrivning"] if kod else "",
        "farligt": int(bool(kod and kod["farligt"])),
        "vikt_kg": vikt or 0,
        "vikt_uppskattad": int(bool(form.get("vikt_uppskattad"))),
        "transportdatum": datum or "",
        "transportsatt": transportsatt,
        "klassgrund": json.dumps(klassgrund),
    }
    kommuner = current_app.config["KOMMUNER"]
    stalle = _arbetsstalle(form.get("arbetsstalle", "")) if roll == "producent" else None
    fran_kommun = "" if stalle else form.get("fran_kommun", "").strip()
    till_kommun = form.get("till_kommun", "").strip()
    data["fran_kommunkod"] = stalle["kommunkod"] if stalle else (kommuner.kod(fran_kommun) or "")
    data["fran_cfar"] = stalle["cfar"] if stalle else ""
    if fran_kommun and not data["fran_kommunkod"]:
        fel.append(f"Okänd kommun: {fran_kommun}.")
    namn, orgnr, adress, kommunkod = _part(form, "mottagare", conn)
    data["mottagare_namn"], data["mottagare_orgnr"] = namn, orgnr
    data["till_adress"] = text["till_adress"] or adress
    data["till_kommunkod"] = kommuner.kod(till_kommun) or kommunkod
    if till_kommun and not kommuner.kod(till_kommun):
        fel.append(f"Okänd kommun: {till_kommun}.")
    if not namn:
        fel.append("Ange mottagare.")
    if not data["till_adress"]:
        fel.append("Ange platsen där avfallet ska hanteras.")
    if roll == "producent":
        namn, orgnr, _, _ = _part(form, "transportor", conn)
        data["transportor_namn"], data["transportor_orgnr"] = namn, orgnr
        data["lamnare_namn"], data["lamnare_orgnr"] = v["namn"], v["orgnr"]
        if stalle:
            data["fran_adress"] = stalle["adress"]
        if not namn:
            fel.append("Ange transportör.")
        if not data["fran_adress"]:
            fel.append("Ange var avfallet producerats.")
    else:
        data["transportor_namn"], data["transportor_orgnr"] = v["namn"], v["orgnr"]
        data["lamnare_namn"] = text["lamnare_namn"] or "Okänd"
        if not data["fran_adress"] and not data["fran_koordinat"]:
            fel.append("Ange platsen där avfallet hämtades, som adress eller koordinat.")
        if not fran_kommun:
            fel.append("Ange kommunen där avfallet hämtades.")
        if data["farligt"] and not klassgrund:
            fel.append("Ange minst en grund för att avfallet bedömts som farligt.")
    return data, fel


@bp.route("/ny/<roll>", methods=["GET", "POST"])
def ny(roll):
    if roll not in ROLLER:
        abort(404)
    conn = get_db()
    if request.method == "POST":
        data, fel = _las_formular(roll, request.form, conn)
        if not fel:
            aid = db.skapa(conn, data, av=request.form.get("av", "").strip())
            flash(f"Anteckning {db.hamta(conn, aid)['lopnr']} sparad.")
            return redirect(url_for("app.visa", aid=aid))
        for f in fel:
            flash(f, "fel")
        varden = _formvarden(request.form)
    else:
        varden = _standardvarden(roll)
        forlaga = request.args.get("kopiera", "")
        if forlaga.isdigit() and (rad := db.hamta(conn, int(forlaga))):
            varden.update({k: v for k, v in _radvarden(rad).items() if k not in KOPIERAS_EJ})
    return render_template("form.html", roll=roll, varden=varden, aid=None, **_formkontext(conn, roll))


@bp.route("/anteckning/<int:aid>/redigera", methods=["GET", "POST"])
def redigera(aid):
    conn = get_db()
    rad = db.hamta(conn, aid) or abort(404)
    if rad["status"] == "makulerad":
        flash("En makulerad anteckning kan inte ändras.", "fel")
        return redirect(url_for("app.visa", aid=aid))
    roll = rad["roll"]
    if request.method == "POST":
        data, fel = _las_formular(roll, request.form, conn)
        if not fel:
            handelse = "rättad" if rad["status"] == "rapporterad" else "ändrad"
            db.uppdatera(conn, aid, data, handelse, av=request.form.get("av", "").strip())
            if handelse == "rättad":
                flash("Anteckningen är rättad. Rätta uppgifterna även i Naturvårdsverkets e-tjänst.", "varning")
            else:
                flash("Anteckningen är ändrad.")
            return redirect(url_for("app.visa", aid=aid))
        for f in fel:
            flash(f, "fel")
        varden = _formvarden(request.form)
        varden["lopnr"] = rad["lopnr"]
    else:
        varden = _radvarden(rad)
    return render_template("form.html", roll=roll, varden=varden, aid=aid, **_formkontext(conn, roll))


@bp.get("/anteckning/<int:aid>")
def visa(aid):
    conn = get_db()
    rad = db.hamta(conn, aid) or abort(404)
    return render_template(
        "detail.html", p=berika(rad), bilagor=db.bilagor(conn, aid), historik=db.historik(conn, aid)
    )


@bp.post("/anteckning/<int:aid>/status")
def status(aid):
    conn = get_db()
    rad = db.hamta(conn, aid) or abort(404)
    form = request.form
    handling = form.get("handling")
    av = form.get("av", "").strip()
    if handling == "rapporterad" and rad["status"] == "antecknad":
        falt = {
            "nv_kvittens": form.get("nv_kvittens", "").strip(),
            "rapporterad_datum": _datum(form.get("rapporterad_datum", "")) or idag().isoformat(),
            "rapporterad_av": form.get("rapporterad_av", "").strip() or av,
        }
        db.satt_status(conn, aid, "rapporterad", falt, "rapporterad", av)
        flash("Markerad som rapporterad.")
    elif handling == "aterta" and rad["status"] == "rapporterad":
        falt = {"nv_kvittens": "", "rapporterad_datum": "", "rapporterad_av": ""}
        db.satt_status(conn, aid, "antecknad", falt, "rapportering återtagen", av)
        flash("Rapporteringen är återtagen.")
    elif handling == "makulera" and rad["status"] != "makulerad":
        skal = form.get("skal", "").strip()
        if not skal:
            flash("Ange skäl för makuleringen.", "fel")
        else:
            notering = f"{rad['notering']}\n" if rad["notering"] else ""
            notering += f"Makulerad {stampel()}: {skal}"
            db.satt_status(conn, aid, "makulerad", {"notering": notering}, "makulerad", av)
            flash("Anteckningen är makulerad.")
    return redirect(url_for("app.visa", aid=aid))


@bp.post("/anteckning/<int:aid>/bilaga")
def ladda_upp(aid):
    conn = get_db()
    rad = db.hamta(conn, aid) or abort(404)
    mapp = current_app.config["DATA"] / "bilagor"
    av = request.form.get("av", "").strip()
    antal = 0
    for fil in request.files.getlist("filer"):
        if not fil.filename:
            continue
        andelse = fil.filename.rsplit(".", 1)[-1].lower() if "." in fil.filename else ""
        if andelse not in BILAGA_TYPER:
            flash(f"{fil.filename}: filtypen stöds inte.", "fel")
            continue
        namn = secure_filename(fil.filename) or f"bilaga.{andelse}"
        lagrad = f"{rad['lopnr']}-{secrets.token_hex(3)}-{namn}"
        fil.save(mapp / lagrad)
        db.lagg_bilaga(conn, aid, fil.filename, lagrad, av)
        antal += 1
    if antal:
        flash(f"{antal} bilaga sparad." if antal == 1 else f"{antal} bilagor sparade.")
    return redirect(url_for("app.visa", aid=aid))


@bp.get("/bilaga/<int:bid>")
def bilaga(bid):
    b = db.hamta_bilaga(get_db(), bid) or abort(404)
    typ = mimetypes.guess_type(b["filnamn"])[0] or "application/octet-stream"
    return send_file(
        current_app.config["DATA"] / "bilagor" / b["lagrad"], mimetype=typ, download_name=b["filnamn"]
    )


def _pdf(data, namn):
    return send_file(io.BytesIO(data), mimetype="application/pdf", download_name=namn, max_age=0)


@bp.get("/anteckning/<int:aid>/anteckning.pdf")
def anteckning_pdf(aid):
    conn = get_db()
    rad = db.hamta(conn, aid) or abort(404)
    p = berika(rad)
    data = pdf.anteckning(p, current_app.config["INST"], db.bilagor(conn, aid), db.historik(conn, aid))
    return _pdf(data, f"anteckning-{p['lopnr']}.pdf")


@bp.get("/anteckning/<int:aid>/transportdokument.pdf")
def transportdokument_pdf(aid):
    rad = db.hamta(get_db(), aid) or abort(404)
    p = berika(rad)
    return _pdf(pdf.transportdokument(p, current_app.config["INST"]), f"transportdokument-{p['lopnr']}.pdf")


@bp.get("/transportdokument.pdf")
def blankett():
    return _pdf(pdf.blankett(current_app.config["INST"]), "transportdokument-blankett.pdf")


@bp.get("/koder.json")
def koder_json():
    lista = [
        {"kod": k["kod"], "beskrivning": k["beskrivning"], "farligt": k["farligt"], "grupp": k["underkapitelnamn"]}
        for k in current_app.config["KODER"].lista
    ]
    svar = jsonify(lista)
    svar.cache_control.max_age = 3600
    return svar


@bp.route("/parter", methods=["GET", "POST"])
def parter():
    conn = get_db()
    if request.method == "POST":
        f = request.form
        kommun = f.get("kommun", "").strip()
        data = {
            "namn": f.get("namn", "").strip(),
            "orgnr": f.get("orgnr", "").strip(),
            "adress": f.get("adress", "").strip(),
            "kommunkod": current_app.config["KOMMUNER"].kod(kommun) or "",
            "roll": f.get("roll") if f.get("roll") in ("transportor", "mottagare", "bada") else "bada",
            "aktiv": int(bool(f.get("aktiv"))),
        }
        if not data["namn"]:
            flash("Ange namn på parten.", "fel")
        elif kommun and not data["kommunkod"]:
            flash(f"Okänd kommun: {kommun}.", "fel")
        else:
            pid = f.get("id", "")
            db.spara_part(conn, int(pid) if pid.isdigit() else None, data)
            flash(f"{data['namn']} sparad.")
        return redirect(url_for("app.parter"))
    return render_template(
        "parter.html", parter=db.parter(conn, aktiva=False), kommuner=current_app.config["KOMMUNER"].lista
    )


@bp.get("/export.csv")
def export():
    conn = get_db()
    ar = request.args.get("ar") or str(idag().year)
    rader = [berika(r) for r in db.lista(conn, None if ar == "alla" else ar)]
    kolumner = [
        "lopnr", "status", "skapad", "andrad", *db.FALT, "fran_kommun", "till_kommun", "senast",
        "nv_kvittens", "rapporterad_datum", "rapporterad_av",
    ]
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(kolumner)
    for p in rader:
        w.writerow(["" if p.get(k) is None else p.get(k) for k in kolumner])
    return Response(
        "﻿" + buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="avfallsanteckningar-{ar}.csv"'},
    )


@bp.get("/api/forfallna")
def api_forfallna():
    oppna = _oppna(get_db())
    return jsonify(
        {
            "att_rapportera": len(oppna),
            "forfallna": [
                {
                    "lopnr": p["lopnr"],
                    "transportdatum": p["transportdatum"],
                    "senast": p["senast"],
                    "dagar": -p["dagar_kvar"],
                }
                for p in oppna
                if p["forsenad"]
            ],
        }
    )


@bp.get("/healthz")
def healthz():
    return jsonify({"ok": True, "version": current_app.config["VERSION"], "anteckningar": db.antal(get_db())})
