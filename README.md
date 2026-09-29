# avfallsanteckning

Anteckningar om farligt avfall enligt 6 kap. avfallsförordningen (2020:614),
för verksamheter som producerar farligt avfall och för dem som själva
transporterar det. Varje anteckning blir ett färdigt underlag för rapporten
till Naturvårdsverkets avfallsregister, som PDF att spara eller skriva ut,
med tidsfristen uträknad i arbetsdagar och en status som visar om rapporten
är lämnad.

Python 3.11+, Flask, SQLite och ReportLab. Ett enda dataverk: en SQLite-fil
och en katalog med bilagor. Gränssnittet är på svenska.

## Vad appen gör

- **Anteckning som producent** (6 kap. 1 §): var avfallet producerats, datum för
  borttransport, transportsätt, transportör, vikt, mottagare och plats.
  Arbetsstället väljs ur en lista, och dess adress, kommun och CFAR-nummer
  följer med in i anteckningen och rapporten.
- **Anteckning som transportör** (6 kap. 2 §): från vem och vilken plats,
  datum, transportsätt, vikt, till vem och vilken plats. Producenten kan vara
  okänd, platsen kan anges med koordinat, och grunden för att avfallet bedömts
  som farligt kryssas i.
- **Avfallskoder** ur bilaga 3 i en sökbar lista, med verksamhetens vanliga
  koder överst. Farliga koder är förvalda, icke-farliga kan visas.
- **Kommuner** anges med namn. SCB:s kommunlista ligger i appen och sätter
  kommunkoden, som avfallsregistret vill ha när producenten är okänd.
- **Tidsfrist**: transportdatum plus två arbetsdagar, med svenska helgdagar
  och regeln om aftnar i lag (1930:173). Försenade anteckningar markeras på
  startsidan och listas på `/api/forfallna` för övervakning.
- **PDF**: anteckningen som dokument, transportdokument enligt 6 kap. 19 § för
  en anteckning, och en tom blankett att ha i bilen eller på verkstaden med
  verksamheten förifylld som transportör.
- **Status**: antecknad, rapporterad med kvittens från e-tjänsten, makulerad
  med skäl. Ingenting raderas. Varje ändring loggas i en historik och en
  ändring efter rapportering märks som rättning.
- **Bilagor**: foto på transportdokument och mottagarkvitto per anteckning.
- **Parter**: återkommande transportörer och mottagare med org.nr och adress.
- **Export**: CSV per år.

Rapporteringen till avfallsregistret görs i Naturvårdsverkets e-tjänst.
Appen ersätter inte den, den ser till att uppgifterna finns i tid och i rätt
form, och att det syns när rapporten är lämnad. Fristen och kodlistan är ett
stöd i arbetet. Ansvaret för att anteckningen är riktig och rapporten lämnad
i tid ligger hos verksamheten.

## Köra

Med Docker, utan att klona repot:

    mkdir avfallsanteckning && cd avfallsanteckning
    curl -O https://raw.githubusercontent.com/mews-se/avfallsanteckning/main/docker-compose.yml
    docker compose up -d

Sidan svarar på port 8400. Fyll i verksamhetens uppgifter under
Inställningar första gången. Bilden `ghcr.io/mews-se/avfallsanteckning`
byggs för amd64 och arm64 och följer `main`; `docker compose pull &&
docker compose up -d` uppdaterar. `./data` innehåller databasen,
bilagorna och logotypen och är det som ska säkerhetskopieras.
Anteckningar ska sparas i minst tre år.

Från källkoden byggs samma bild med `docker build -t avfallsanteckning .`.

Utan Docker:

    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    AVFALLSANTECKNING_HOST=0.0.0.0 .venv/bin/python -m avfallsanteckning

Miljövariabler: `AVFALLSANTECKNING_DATA` (standard `data`),
`AVFALLSANTECKNING_HOST`, `AVFALLSANTECKNING_PORT`.

Appen har ingen inloggning. Kör den på det egna nätet eller bakom en
reverse proxy med inloggning.

## Inställningar

Allt som är eget för verksamheten skrivs in under Inställningar i appen
och sparas i databasen:

- **Verksamhet**: namn, org.nr, adress, kommun, CFAR-nummer och
  kontaktadress. CFAR-numret är arbetsställets nummer hos SCB och krävs i
  producentrapporter. Kontaktadressen skrivs ut på blanketten som den
  adress dit den fotograferade blanketten ska mejlas.
- **Logotyp** i sidhuvudet. Utan logotyp visas verksamhetens namn.
- **Arbetsställen** att välja bland där avfallet producerats, med varsitt
  CFAR-nummer. Utan egna arbetsställen används verksamhetens adress och
  CFAR-nummer.
- **Vanliga avfallskoder**, som ligger överst i kodväljaren.
- **Transportör**: slår på anteckningar som transportör och den tomma
  blanketten, för verksamheter som själva transporterar farligt avfall.
  Här sätts blankettens beskrivningsrad, en förtryckt producent (till
  exempel att den är okänd när avfallet är upphittat; utan text finns en
  ifyllningsrad och producentens underskrift) och grunderna att kryssa i
  för att avfallet bedömts som farligt, på blanketten och i
  transportörsanteckningen.

Org.nr kontrolleras mot kontrollsiffran och sparas som 556xxx-xxxx, på
Inställningar, på Parter och i anteckningarna. Vid fälten finns länkar
till SCB:s sökning av arbetsställen med CFAR-nummer och till
Bolagsverkets företagssökning. Båda är fria att använda.

## Avfallskoder och kommuner

`avfallsanteckning/data/avfallskoder.json` byggs av `tools/avfallskoder.py`
ur förordningstexten i riksdagens öppna data (källa: Sveriges riksdag). Kör
skriptet igen när bilaga 3 ändras; ändringar med senare ikraftträdande ligger
redan i listan med sina datum. `avfallsanteckning/data/kommuner.json` byggs
av `tools/kommuner.py` ur SCB:s lista över kommuner i kodnummerordning
(källa: SCB).

## Tester

    python3 -m unittest discover -s tests
