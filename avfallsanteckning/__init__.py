import os
import secrets
from pathlib import Path

from flask import Flask

from . import config, db, koder, kommuner

__version__ = "0.1.0"


def create_app(config_path=None, data_dir=None):
    app = Flask(__name__)
    data = Path(data_dir or os.environ.get("AVFALLSANTECKNING_DATA", "data"))
    (data / "bilagor").mkdir(parents=True, exist_ok=True)
    kommunlista = kommuner.Kommuner.load()
    inst = config.load(config_path)
    v = inst["verksamhet"]
    v["kommunkod"] = kommunlista.kod(v["kommun"] or v["kommunkod"]) or ""
    v["kommun"] = kommunlista.namn(v["kommunkod"])
    for s in inst["arbetsstallen"]:
        s["kommunkod"] = kommunlista.kod(s["kommun"]) or ""
        s["kommun"] = kommunlista.namn(s["kommunkod"]) or s["kommun"]
    app.config.update(
        SECRET_KEY=_hemlighet(data / "secret"),
        MAX_CONTENT_LENGTH=25 * 1024 * 1024,
        INST=inst,
        DATA=data,
        DB_PATH=data / "avfallsanteckning.db",
        KODER=koder.Koder.load(),
        KOMMUNER=kommunlista,
        VERSION=__version__,
    )
    db.init(app.config["DB_PATH"])

    from .views import bp

    app.register_blueprint(bp)
    return app


def _hemlighet(path):
    if not path.exists():
        path.write_text(secrets.token_hex(32))
    return path.read_text().strip()
