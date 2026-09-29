import os
import secrets
from pathlib import Path

from flask import Flask

from . import db, koder, kommuner, kommungranser

__version__ = "0.1.0"


def create_app(data_dir=None):
    app = Flask(__name__)
    data = Path(data_dir or os.environ.get("AVFALLSANTECKNING_DATA", "data"))
    (data / "bilagor").mkdir(parents=True, exist_ok=True)
    app.config.update(
        SECRET_KEY=_hemlighet(data / "secret"),
        MAX_CONTENT_LENGTH=25 * 1024 * 1024,
        DATA=data,
        DB_PATH=data / "avfallsanteckning.db",
        KODER=koder.Koder.load(),
        KOMMUNER=kommuner.Kommuner.load(),
        GRANSER=kommungranser.Kommungranser.load(),
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
