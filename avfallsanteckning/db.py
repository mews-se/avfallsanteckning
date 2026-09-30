import json
import sqlite3

from .tid import stampel

SCHEMA = """
CREATE TABLE IF NOT EXISTS anteckning (
    id INTEGER PRIMARY KEY,
    lopnr TEXT NOT NULL UNIQUE,
    roll TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'antecknad',
    skapad TEXT NOT NULL,
    andrad TEXT NOT NULL,
    avfallskod TEXT NOT NULL,
    avfallstyp TEXT NOT NULL,
    farligt INTEGER NOT NULL,
    vikt_kg REAL NOT NULL,
    vikt_uppskattad INTEGER NOT NULL DEFAULT 0,
    transportdatum TEXT NOT NULL,
    transportsatt TEXT NOT NULL,
    lamnare_namn TEXT NOT NULL DEFAULT '',
    lamnare_orgnr TEXT NOT NULL DEFAULT '',
    fran_adress TEXT NOT NULL DEFAULT '',
    fran_kommunkod TEXT NOT NULL DEFAULT '',
    fran_koordinat TEXT NOT NULL DEFAULT '',
    fran_cfar TEXT NOT NULL DEFAULT '',
    transportor_namn TEXT NOT NULL DEFAULT '',
    transportor_orgnr TEXT NOT NULL DEFAULT '',
    mottagare_namn TEXT NOT NULL DEFAULT '',
    mottagare_orgnr TEXT NOT NULL DEFAULT '',
    till_adress TEXT NOT NULL DEFAULT '',
    till_kommunkod TEXT NOT NULL DEFAULT '',
    klassgrund TEXT NOT NULL DEFAULT '[]',
    fordon TEXT NOT NULL DEFAULT '',
    forare TEXT NOT NULL DEFAULT '',
    referens TEXT NOT NULL DEFAULT '',
    notering TEXT NOT NULL DEFAULT '',
    nv_kvittens TEXT NOT NULL DEFAULT '',
    rapporterad_datum TEXT NOT NULL DEFAULT '',
    rapporterad_av TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS historik (
    id INTEGER PRIMARY KEY,
    anteckning_id INTEGER NOT NULL REFERENCES anteckning(id),
    tidpunkt TEXT NOT NULL,
    handelse TEXT NOT NULL,
    av TEXT NOT NULL DEFAULT '',
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bilaga (
    id INTEGER PRIMARY KEY,
    anteckning_id INTEGER NOT NULL REFERENCES anteckning(id),
    filnamn TEXT NOT NULL,
    lagrad TEXT NOT NULL,
    tidpunkt TEXT NOT NULL,
    av TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS installning (
    sektion TEXT PRIMARY KEY,
    varde TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS part (
    id INTEGER PRIMARY KEY,
    namn TEXT NOT NULL,
    orgnr TEXT NOT NULL DEFAULT '',
    adress TEXT NOT NULL DEFAULT '',
    kommunkod TEXT NOT NULL DEFAULT '',
    roll TEXT NOT NULL DEFAULT 'bada',
    aktiv INTEGER NOT NULL DEFAULT 1
);
"""

FALT = (
    "roll", "avfallskod", "avfallstyp", "farligt", "vikt_kg", "vikt_uppskattad",
    "transportdatum", "transportsatt", "lamnare_namn", "lamnare_orgnr", "fran_adress",
    "fran_kommunkod", "fran_koordinat", "fran_cfar", "transportor_namn", "transportor_orgnr",
    "mottagare_namn", "mottagare_orgnr", "till_adress", "till_kommunkod", "klassgrund",
    "fordon", "forare", "referens", "notering",
)

AVFALLSFALT = ("avfallskod", "avfallstyp", "farligt", "vikt_kg", "vikt_uppskattad")

PARTFALT = ("namn", "orgnr", "adress", "kommunkod", "roll", "aktiv")


def anslut(path):
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init(path):
    conn = anslut(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        kolumner = {r[1] for r in conn.execute("PRAGMA table_info(anteckning)")}
        if "fran_cfar" not in kolumner:
            conn.execute("ALTER TABLE anteckning ADD COLUMN fran_cfar TEXT NOT NULL DEFAULT ''")
    finally:
        conn.close()


def nytt_lopnr(conn, ar):
    rad = conn.execute(
        "SELECT max(lopnr) FROM anteckning WHERE lopnr LIKE ?", (f"{ar}-%",)
    ).fetchone()
    n = int(rad[0].split("-")[1]) + 1 if rad[0] else 1
    return f"{ar}-{n:04d}"


def skapa(conn, data, av=""):
    nu = stampel()
    kolumner = ", ".join(FALT)
    platser = ", ".join("?" * len(FALT))
    for _ in range(5):
        lopnr = nytt_lopnr(conn, nu[:4])
        try:
            with conn:
                cur = conn.execute(
                    f"INSERT INTO anteckning (lopnr, status, skapad, andrad, {kolumner})"
                    f" VALUES (?, 'antecknad', ?, ?, {platser})",
                    [lopnr, nu, nu, *(data[f] for f in FALT)],
                )
                _logga(conn, cur.lastrowid, "skapad", data, av)
                return cur.lastrowid
        except sqlite3.IntegrityError:
            continue
    raise RuntimeError("kunde inte tilldela löpnummer")


def uppdatera(conn, aid, data, handelse, av=""):
    satt = ", ".join(f"{f} = ?" for f in FALT)
    with conn:
        conn.execute(
            f"UPDATE anteckning SET {satt}, andrad = ? WHERE id = ?",
            [*(data[f] for f in FALT), stampel(), aid],
        )
        _logga(conn, aid, handelse, data, av)


def satt_status(conn, aid, status, falt, handelse, av=""):
    satt = "".join(f", {f} = ?" for f in falt)
    with conn:
        conn.execute(
            f"UPDATE anteckning SET status = ?{satt}, andrad = ? WHERE id = ?",
            [status, *falt.values(), stampel(), aid],
        )
        _logga(conn, aid, handelse, {"status": status, **falt}, av)


def _logga(conn, aid, handelse, data, av):
    conn.execute(
        "INSERT INTO historik (anteckning_id, tidpunkt, handelse, av, data) VALUES (?, ?, ?, ?, ?)",
        (aid, stampel(), handelse, av, json.dumps(data, ensure_ascii=False)),
    )


def hamta(conn, aid):
    return conn.execute("SELECT * FROM anteckning WHERE id = ?", (aid,)).fetchone()


def lista(conn, ar=None, roll=None, status=None):
    villkor, param = ["1 = 1"], []
    if ar:
        villkor.append("lopnr LIKE ?")
        param.append(f"{ar}-%")
    if roll:
        villkor.append("roll = ?")
        param.append(roll)
    if status:
        villkor.append("status = ?")
        param.append(status)
    return conn.execute(
        f"SELECT * FROM anteckning WHERE {' AND '.join(villkor)}"
        " ORDER BY transportdatum DESC, lopnr",
        param,
    ).fetchall()


def antal(conn):
    return conn.execute("SELECT count(*) FROM anteckning").fetchone()[0]


def ar_lista(conn):
    return [
        r[0]
        for r in conn.execute("SELECT DISTINCT substr(lopnr, 1, 4) FROM anteckning ORDER BY 1 DESC")
    ]


def historik(conn, aid):
    return conn.execute(
        "SELECT * FROM historik WHERE anteckning_id = ? ORDER BY id", (aid,)
    ).fetchall()


def bilagor(conn, aid):
    return conn.execute(
        "SELECT * FROM bilaga WHERE anteckning_id = ? ORDER BY id", (aid,)
    ).fetchall()


def lagg_bilaga(conn, aid, filnamn, lagrad, av=""):
    with conn:
        cur = conn.execute(
            "INSERT INTO bilaga (anteckning_id, filnamn, lagrad, tidpunkt, av) VALUES (?, ?, ?, ?, ?)",
            (aid, filnamn, lagrad, stampel(), av),
        )
        return cur.lastrowid


def hamta_bilaga(conn, bid):
    return conn.execute("SELECT * FROM bilaga WHERE id = ?", (bid,)).fetchone()


def parter(conn, roll=None, aktiva=True):
    villkor, param = ["1 = 1"], []
    if aktiva:
        villkor.append("aktiv = 1")
    if roll:
        villkor.append("roll IN (?, 'bada')")
        param.append(roll)
    return conn.execute(
        f"SELECT * FROM part WHERE {' AND '.join(villkor)} ORDER BY namn COLLATE NOCASE", param
    ).fetchall()


def part(conn, pid):
    return conn.execute("SELECT * FROM part WHERE id = ?", (pid,)).fetchone()


def spara_part(conn, pid, data):
    with conn:
        if pid:
            satt = ", ".join(f"{f} = ?" for f in PARTFALT)
            conn.execute(f"UPDATE part SET {satt} WHERE id = ?", [*(data[f] for f in PARTFALT), pid])
            return pid
        cur = conn.execute(
            f"INSERT INTO part ({', '.join(PARTFALT)}) VALUES ({', '.join('?' * len(PARTFALT))})",
            [data[f] for f in PARTFALT],
        )
        return cur.lastrowid


def installningar(conn):
    return {r["sektion"]: json.loads(r["varde"]) for r in conn.execute("SELECT sektion, varde FROM installning")}


def spara_installningar(conn, data):
    with conn:
        for sektion, varde in data.items():
            conn.execute(
                "INSERT INTO installning (sektion, varde) VALUES (?, ?)"
                " ON CONFLICT(sektion) DO UPDATE SET varde = excluded.varde",
                (sektion, json.dumps(varde, ensure_ascii=False)),
            )
