from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Stockholm")


def nu():
    return datetime.now(TZ)


def idag():
    return nu().date()


def stampel():
    return nu().strftime("%Y-%m-%d %H:%M")
