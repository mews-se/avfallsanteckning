from datetime import date, timedelta


def paskdagen(ar):
    a = ar % 19
    b, c = divmod(ar, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    manad, dag = divmod(h + m - 7 * n + 114, 31)
    return date(ar, manad, dag + 1)


def _lordag_fran(ar, manad, dag):
    d = date(ar, manad, dag)
    return d + timedelta(days=(5 - d.weekday()) % 7)


def helgdagar(ar):
    pask = paskdagen(ar)
    return {
        date(ar, 1, 1),
        date(ar, 1, 6),
        pask - timedelta(days=2),
        pask,
        pask + timedelta(days=1),
        date(ar, 5, 1),
        pask + timedelta(days=39),
        pask + timedelta(days=49),
        date(ar, 6, 6),
        _lordag_fran(ar, 6, 20),
        _lordag_fran(ar, 10, 31),
        date(ar, 12, 25),
        date(ar, 12, 26),
    }


def aftnar(ar):
    return {_lordag_fran(ar, 6, 20) - timedelta(days=1), date(ar, 12, 24), date(ar, 12, 31)}


def arbetsdag(d):
    return d.weekday() < 5 and d not in helgdagar(d.year)


def plus_arbetsdagar(d, n):
    while n > 0:
        d += timedelta(days=1)
        if arbetsdag(d):
            n -= 1
    # lag (1930:173): en frist som slutar på midsommar-, jul- eller nyårsafton löper till nästa vardag
    while d in aftnar(d.year) or not arbetsdag(d):
        d += timedelta(days=1)
    return d


def rapportera_senast(transportdatum):
    return plus_arbetsdagar(transportdatum, 2)
