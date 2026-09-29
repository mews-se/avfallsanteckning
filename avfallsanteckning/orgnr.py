import re

_EJ_SIFFRA = re.compile(r"\D")


def _siffror(text):
    s = _EJ_SIFFRA.sub("", text or "")
    # tolv siffror är sekelprefix plus tio, som 16556000-0001 eller ett personnummer
    return s[2:] if len(s) == 12 else s


def giltigt(text):
    s = _siffror(text)
    if len(s) != 10:
        return False
    summa = 0
    for i, c in enumerate(s):
        n = int(c) * (2 if i % 2 == 0 else 1)
        summa += n - 9 if n > 9 else n
    return summa % 10 == 0


def formatera(text):
    s = _siffror(text)
    return f"{s[:6]}-{s[6:]}" if len(s) == 10 else text.strip()
