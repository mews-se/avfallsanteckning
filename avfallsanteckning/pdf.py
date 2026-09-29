import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .texter import GRUND, KLASSGRUNDER, ROLLER, STATUS
from .tid import stampel

# sidbredd minus marginaler och ramens egen indragning om 6 pt per sida
BREDD = A4[0] - 40 * mm - 12
GRA = colors.HexColor("#555555")
LINJE = colors.HexColor("#bbbbbb")

RUBRIK = ParagraphStyle("rubrik", fontName="Helvetica-Bold", fontSize=16, leading=20)
UNDER = ParagraphStyle("under", fontName="Helvetica", fontSize=9, leading=12, textColor=GRA)
TEXT = ParagraphStyle("text", fontName="Helvetica", fontSize=9.5, leading=12.5)
ETIKETT = ParagraphStyle("etikett", fontName="Helvetica", fontSize=8.5, leading=11, textColor=GRA)
AVSNITT = ParagraphStyle(
    "avsnitt", fontName="Helvetica-Bold", fontSize=10.5, leading=13, spaceBefore=5 * mm, spaceAfter=1.5 * mm
)


def _t(s):
    s = str(s) if s not in (None, "") else "–"
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")


def _tabell(rader, tom=False):
    data = [[Paragraph(_t(k), ETIKETT), Paragraph("" if tom and not v else _t(v), TEXT)] for k, v in rader]
    t = Table(
        data,
        colWidths=[52 * mm, BREDD - 52 * mm],
        rowHeights=[10 * mm] * len(data) if tom else None,
    )
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE" if tom else "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINJE),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def _signatur(rubrik):
    rader = [
        [Paragraph(f"<b>{_t(rubrik)}</b>", TEXT)],
        [""],
        [Paragraph("Underskrift", ETIKETT)],
        [""],
        [Paragraph("Namnförtydligande", ETIKETT)],
        [""],
        [Paragraph("Ort och datum", ETIKETT)],
    ]
    hojder = [6 * mm, 11 * mm, 5 * mm, 9 * mm, 5 * mm, 9 * mm, 5 * mm]
    t = Table(rader, colWidths=[BREDD / 2 - 8 * mm], rowHeights=hojder)
    t.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 2), (0, 2), 0.5, colors.black),
                ("LINEABOVE", (0, 4), (0, 4), 0.5, colors.black),
                ("LINEABOVE", (0, 6), (0, 6), 0.5, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return t


def _underskrifter(producent=True):
    block = [_signatur("Producent"), _signatur("Transportör")] if producent else [_signatur("Transportör"), ""]
    t = Table([block], colWidths=[BREDD / 2, BREDD / 2])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    rubrik = "Underskrifter" if producent else "Underskrift"
    return KeepTogether([Paragraph(rubrik, AVSNITT), t])


def _okand(namn):
    return namn.strip().lower() in ("", "okänd")


def _bygg(titel, under, inst, delar, sidfot):
    v = inst["verksamhet"]
    huvud = " · ".join(x for x in (v["namn"], f"Org.nr {v['orgnr']}" if v["orgnr"] else "", v["adressrad"]) if x)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=titel,
        author=v["namn"] or "avfallsanteckning",
    )

    def fot(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(GRA)
        canvas.drawString(20 * mm, 9 * mm, sidfot)
        canvas.drawRightString(A4[0] - 20 * mm, 9 * mm, f"Sida {d.page}")
        canvas.restoreState()

    ingress = [Paragraph(_t(titel), RUBRIK), Paragraph(_t(under), UNDER), Paragraph(_t(huvud), UNDER)]
    doc.build([*ingress, Spacer(1, 3 * mm), *delar], onFirstPage=fot, onLaterPages=fot)
    return buf.getvalue()


def _vikt(p):
    s = f"{float(p['vikt_kg']):,.1f}".replace(",", "\N{NO-BREAK SPACE}").replace(".", ",")
    return f"{s.rstrip('0').rstrip(',')} kg" + (" (uppskattad)" if p["vikt_uppskattad"] else "")


def _part(namn, orgnr):
    return f"{namn} ({orgnr})" if namn and orgnr else namn


def _kommun(p, riktning):
    namn, kod = p[f"{riktning}_kommun"], p[f"{riktning}_kommunkod"]
    return f"{namn} ({kod})" if namn else kod


def _plats(adress, kommun="", koordinat="", cfar=""):
    delar = [adress, koordinat, f"kommun {kommun}" if kommun else "", f"CFAR {cfar}" if cfar else ""]
    return " · ".join(x for x in delar if x)


def _avfall(p):
    return f"{p['avfallskod']} {p['avfallstyp']}"


def anteckning(p, inst, bilagor=(), historik=()):
    farligt = bool(p["farligt"])
    titel = "Anteckning om farligt avfall" if farligt else "Anteckning om avfall"
    under = f"{GRUND[p['roll']]} · {ROLLER[p['roll']]} · Löpnr {p['lopnr']}"
    delar = [
        Paragraph("Avfall", AVSNITT),
        _tabell([("Avfallstyp", _avfall(p)), ("Farligt avfall", "Ja" if farligt else "Nej"), ("Vikt", _vikt(p))]),
    ]
    if p["roll"] == "producent":
        rader = [
            ("Var avfallet producerats", _plats(p["fran_adress"], _kommun(p, "fran"), cfar=p["fran_cfar"])),
            ("Datum för borttransport", p["transportdatum"]),
            ("Transportsätt", p["transportsatt"]),
            ("Transportör", _part(p["transportor_namn"], p["transportor_orgnr"])),
            ("Mottagare", _part(p["mottagare_namn"], p["mottagare_orgnr"])),
            ("Plats där avfallet ska hanteras", _plats(p["till_adress"], _kommun(p, "till"))),
        ]
    else:
        rader = [
            ("Från vem", _part(p["lamnare_namn"], p["lamnare_orgnr"])),
            ("Från vilken plats", _plats(p["fran_adress"], _kommun(p, "fran"), p["fran_koordinat"])),
            ("Datum för transport", p["transportdatum"]),
            ("Transportsätt", p["transportsatt"]),
            ("Transportör", _part(p["transportor_namn"], p["transportor_orgnr"])),
            ("Till vem", _part(p["mottagare_namn"], p["mottagare_orgnr"])),
            ("Till vilken plats", _plats(p["till_adress"], _kommun(p, "till"))),
        ]
        if p["klassgrund_lista"]:
            rader.append(("Grund för bedömningen farligt avfall", "\n".join(p["klassgrund_lista"])))
        rader += [("Fordon", p["fordon"]), ("Förare", p["forare"])]
    rader += [("Referens", p["referens"]), ("Notering", p["notering"])]
    delar += [Paragraph("Transport", AVSNITT), _tabell(rader)]

    rap = [("Status", STATUS[p["status"]])]
    if farligt:
        rap.append(("Rapporteras till avfallsregistret senast", p["senast"]))
    if p["status"] == "rapporterad":
        rap += [
            ("Rapporterad", f"{p['rapporterad_datum']} av {p['rapporterad_av']}".strip(" av")),
            ("Kvittens från Naturvårdsverket", p["nv_kvittens"]),
        ]
    delar += [Paragraph("Rapportering", AVSNITT), _tabell(rap)]

    av = next((h["av"] for h in historik if h["handelse"] == "skapad"), "")
    ant = [("Antecknad", f"{p['skapad']}" + (f" av {av}" if av else "")), ("Senast ändrad", p["andrad"])]
    if bilagor:
        ant.append(("Bilagor", "\n".join(b["filnamn"] for b in bilagor)))
    delar += [Paragraph("Anteckningen", AVSNITT), _tabell(ant)]
    sidfot = f"Avfallsanteckning · {p['lopnr']} · utskriven {stampel()} · sparas i minst tre år (6 kap. 6 §)"
    return _bygg(titel, under, inst, delar, sidfot)


def _transportrader(p):
    return [
        ("Avfallstyp", _avfall(p) if p else ""),
        ("Vikt i kilogram", _vikt(p) if p else ""),
        ("Datum för transporten", p["transportdatum"] if p else ""),
        ("Ursprunglig plats", _plats(p["fran_adress"], _kommun(p, "fran"), p["fran_koordinat"]) if p else ""),
        ("Slutlig plats", _plats(p["till_adress"], _kommun(p, "till")) if p else ""),
        ("Transportör", _part(p["transportor_namn"], p["transportor_orgnr"]) if p else ""),
        ("Producent", _part(p["lamnare_namn"], p["lamnare_orgnr"]) if p else ""),
        ("Slutlig mottagare", _part(p["mottagare_namn"], p["mottagare_orgnr"]) if p else ""),
    ]


def transportdokument(p, inst):
    under = f"6 kap. 19 § avfallsförordningen (2020:614) · Löpnr {p['lopnr']}"
    delar = [Paragraph("Transporten", AVSNITT), _tabell(_transportrader(p))]
    if p["fordon"] or p["forare"]:
        delar.append(_tabell([("Fordon", p["fordon"]), ("Förare", p["forare"])]))
    # vid okänd producent finns ingen som kan skriva under för den sidan
    delar.append(_underskrifter(producent=not _okand(p["lamnare_namn"])))
    sidfot = f"Avfallsanteckning · {p['lopnr']} · utskriven {stampel()}"
    return _bygg("Transportdokument för farligt avfall", under, inst, delar, sidfot)


def blankett(inst):
    v = inst["verksamhet"]
    rader = _transportrader(None)
    rader[5] = ("Transportör", _part(v["namn"], v["orgnr"]))
    rader.insert(7, ("Fordon och förare", ""))
    rader.append(("Referens, händelse eller uppdrag", ""))
    tabell = _tabell(rader, tom=True)
    kryss = "<br/>".join(f"[  ] {_t(text)}" for _, text in KLASSGRUNDER)
    bedomning = [
        Paragraph("Bedömning på plats", AVSNITT),
        Paragraph(
            "Transportdokument upprättas när avfallet bedöms som farligt avfall. Kryssa den eller de "
            "omständigheter som ligger till grund för bedömningen.",
            ETIKETT,
        ),
        Spacer(1, 2 * mm),
        Paragraph(kryss, TEXT),
    ]
    delar = [Paragraph("Transporten", AVSNITT), tabell, *bedomning, _underskrifter()]
    delar.append(Spacer(1, 4 * mm))
    if v["kontakt"]:
        instruktion = f"<b>Fotografera den ifyllda blanketten och mejla bilden omgående till {_t(v['kontakt'])}.</b>"
    else:
        instruktion = "Fotografera den ifyllda blanketten och lämna bilden till den som för anteckningarna samma dag."
    delar.append(
        Paragraph(
            f"{instruktion} Uppgifterna rapporteras till Naturvårdsverkets avfallsregister senast två arbetsdagar "
            "efter transporten.",
            TEXT,
        )
    )
    sidfot = f"Avfallsanteckning · tom blankett utskriven {stampel()}"
    under = "Tom blankett att fylla i för hand · 6 kap. 19 § avfallsförordningen (2020:614)"
    return _bygg("Transportdokument för farligt avfall", under, inst, delar, sidfot)
