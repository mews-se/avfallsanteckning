import os

from . import create_app

create_app().run(
    host=os.environ.get("AVFALLSANTECKNING_HOST", "127.0.0.1"),
    port=int(os.environ.get("AVFALLSANTECKNING_PORT", "8400")),
)
