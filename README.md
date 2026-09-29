# avfallsanteckning

[![CI](https://github.com/mews-se/avfallsanteckning/actions/workflows/ci.yml/badge.svg)](https://github.com/mews-se/avfallsanteckning/actions/workflows/ci.yml)
[![Image](https://github.com/mews-se/avfallsanteckning/actions/workflows/image.yml/badge.svg)](https://github.com/mews-se/avfallsanteckning/actions/workflows/image.yml)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.13-3776AB?logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
[![licens](https://img.shields.io/badge/licens-MIT-green)](LICENSE)

Anteckningar om farligt avfall enligt 6 kap. avfallsförordningen
(2020:614), för verksamheter som producerar farligt avfall och för dem som
själva transporterar det. Varje anteckning blir ett färdigt underlag för
rapporten till Naturvårdsverkets avfallsregister, med tidsfristen uträknad i
arbetsdagar, en status som visar om rapporten är lämnad, och PDF att spara
eller skriva ut. Självhostad på eget nätverk: en container, en datakatalog,
inga konton hos någon tredje part.

## Bakgrund

Den som producerar farligt avfall i en yrkesmässig verksamhet ska anteckna
uppgifter om avfallet innan det transporteras bort: var det uppkommit,
datum, transportsätt, transportör, vikt, mottagare och var det ska tas
om hand. Den som själv transporterar farligt avfall ska anteckna
motsvarande om varje transport. Uppgifterna ska rapporteras till
Naturvårdsverkets avfallsregister senast två arbetsdagar efter att
anteckningen skulle vara förd, och anteckningarna ska sparas i tre år,
transportörens i tolv månader. En rapport som uteblir eller kommer för
sent kostar en miljösanktionsavgift på 5 000 kr per rapport.

Kravet är enkelt men lätt att missa i vardagen, särskilt när hämtningarna
är få och avfallsentreprenören rapporterar i sin egen roll. Appen gör
anteckningen till ett formulär med rätt fält, räknar ut fristen och håller
reda på vad som är rapporterat.

Rapporteringen görs i [Naturvårdsverkets e-tjänst](https://www.naturvardsverket.se/verktyg-och-tjanster/e-tjanster/avfallsregistret/).
Appen ersätter inte den, den ser till att uppgifterna finns i tid och i
rätt form, och att det syns när rapporten är lämnad. Fristen och kodlistan
är ett stöd i arbetet. Ansvaret för att anteckningen är riktig och
rapporten lämnad i tid ligger hos verksamheten.

## Funktioner

- **Anteckning som producent** (6 kap. 1 §): arbetsstället väljs ur en
  lista och dess adress, kommun och CFAR-nummer följer med in i
  anteckningen. Transportör och mottagare väljs bland sparade parter eller
  skrivs in.
- **Anteckning som transportör** (6 kap. 2 §), för verksamheter som själva
  kör farligt avfall: från vem och vilken plats, med adress eller koordinat,
  producenten kan vara okänd, och grunden för att avfallet bedömts som
  farligt kryssas i.
- **Avfallskoder** ur bilaga 3 i en sökbar lista, med verksamhetens vanliga
  koder överst. Farliga koder är förvalda, icke-farliga kan visas. Listan
  bär både dagens lydelse och den som gäller från den 9 december 2026 och
  väljer rätt lydelse efter datum.
- **Kommuner** anges med namn. SCB:s kommunlista sätter kommunkoden, som
  avfallsregistret vill ha när producenten är okänd.
- **Tidsfrist**: transportdatum plus två arbetsdagar, med svenska helgdagar
  och regeln om aftnar i lag (1930:173). Startsidan visar dagar kvar och
  markerar det som är försenat.
- **Status och historik**: antecknad, rapporterad med kvittens från
  e-tjänsten, makulerad med skäl. Ingenting raderas. Varje ändring loggas,
  och en ändring efter rapportering märks som rättning med en påminnelse om
  att rätta även i e-tjänsten.
- **Dokument**: anteckningen som PDF, transportdokument enligt 6 kap. 19 §
  för en anteckning, och en tom blankett att ha i bilen eller på verkstaden
  med verksamheten förifylld som transportör.
- **Bilagor**: foto på transportdokumentet och mottagarens kvitto per
  anteckning, som PDF, JPG, PNG, HEIC eller WebP upp till 25 MB.
- **Parter**: återkommande transportörer och mottagare med org.nr, adress
  och kommun. Org.nr kontrolleras mot kontrollsiffran.
- **Export** som CSV per år, och en JSON-adress för övervakning av
  försenade rapporter.

## Komma igång

Med Docker, utan att klona repot:

```bash
mkdir avfallsanteckning && cd avfallsanteckning
curl -O https://raw.githubusercontent.com/mews-se/avfallsanteckning/main/docker-compose.yml
docker compose up -d
```

Sidan svarar på `http://localhost:8400`. Fyll i verksamhetens uppgifter under
Inställningar första gången; startsidan säger till tills det är gjort.

Bilden `ghcr.io/mews-se/avfallsanteckning` byggs för amd64 och arm64 och
följer `main`. Uppdatera med:

```bash
docker compose pull && docker compose up -d
```

Från källkoden byggs samma bild med `docker build -t avfallsanteckning .`.
Utan Docker:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
AVFALLSANTECKNING_HOST=0.0.0.0 .venv/bin/python -m avfallsanteckning
```

Miljövariabler: `AVFALLSANTECKNING_DATA` (standard `data`),
`AVFALLSANTECKNING_HOST` (standard `127.0.0.1`) och `AVFALLSANTECKNING_PORT`
(standard `8400`).

Appen har ingen inloggning. Kör den på det egna nätet eller bakom en
reverse proxy med inloggning, och exponera den inte mot internet.

## Inställningar

Allt som är eget för verksamheten skrivs in under Inställningar i appen
och sparas i databasen:

- **Verksamhet**: namn, org.nr, adress, CFAR-nummer och kontaktadress.
  CFAR-numret är arbetsställets nummer hos SCB och krävs i
  producentrapporter. Kontaktadressen skrivs ut på blanketten som den
  adress dit den fotograferade blanketten ska mejlas.
- **Logotyp** i sidhuvudet. Utan logotyp visas verksamhetens namn.
- **Arbetsställen** att välja bland där avfallet producerats, med varsitt
  CFAR-nummer och kommun. Utan egna arbetsställen används verksamhetens
  adress och CFAR-nummer, och postorten räknas som kommun när den är en.
- **Vanliga avfallskoder**, som ligger överst i kodväljaren.
- **Transportör**: slår på anteckningar som transportör och den tomma
  blanketten. Här sätts blankettens beskrivningsrad, en förtryckt
  producent (till exempel att den är okänd när avfallet är upphittat; utan
  text finns en ifyllningsrad och producentens underskrift) och grunderna
  att kryssa i för att avfallet bedömts som farligt, på blanketten och i
  transportörsanteckningen.

Vid fälten finns länkar till SCB:s sökning av arbetsställen med
CFAR-nummer, Bolagsverkets företagssökning, länsstyrelsernas register över
avfallstransportörer och Naturvårdsverkets vägledning. Alla är fria att
använda.

## Så används appen

1. **Anteckna innan transporten.** Ny: producent, välj arbetsställe,
   avfallskod, vikt, transportör och mottagare. Anteckningen får ett löpnummer
   per år, som `2026-0001`, och kan skrivas ut som PDF.
2. **Rapportera i e-tjänsten** inom två arbetsdagar. Anteckningssidan visar
   fristen och länkar till e-tjänsten. Uppgifterna förs över därifrån.
3. **Markera som rapporterad** med kvittensen från e-tjänsten, datum och vem
   som rapporterade, även när ett ombud gjorde det.
4. **Lägg bilagor**: transportdokumentet och mottagarens kvitto, så att hela
   underlaget finns på ett ställe i tre år.
5. **Rätta vid behov.** En ändring efter rapportering loggas som rättning.
   Fel anteckning makuleras med skäl och står kvar överstruken.

För den som transporterar själv finns Ny: transportör och blanketten, som
skrivs ut i förväg och fylls i för hand på plats. Fotografera den ifyllda
blanketten och mejla den till kontaktadressen, så förs anteckningen in i
appen samma dag.

## Data och drift

`./data` innehåller databasen `avfallsanteckning.db`, katalogen `bilagor`,
logotypen och en hemlighet för sessionerna. Det är hela tillståndet och det
som ska säkerhetskopieras. Databasen är SQLite i WAL-läge, så kopiera den
med `sqlite3 avfallsanteckning.db ".backup kopia.db"` eller med containern
stoppad.

Containern kör som root, och compose-filens `init: true` gör att `docker
compose stop` avslutar den direkt. Bilden byggs om varje vecka så att basbilden
hålls uppdaterad; automatiska uppdaterare som Watchtower fungerar.

För övervakning:

- `/healthz` svarar `{"ok": true, "version": "…", "anteckningar": n}`.
- `/api/forfallna` svarar med antalet farliga anteckningar som ännu inte är
  rapporterade och en lista över de försenade, med löpnummer, transportdatum,
  sista rapportdag och antal dagar försenad.

Exporten `/export.csv?ar=2026` (eller `ar=alla`) ger en semikolonseparerad
fil med BOM, som öppnas rätt i Excel, med alla fält i anteckningen samt
kommunnamn, frist, kvittens och rapporteringsuppgifter.

## Datakällor

`avfallsanteckning/data/avfallskoder.json` byggs av `tools/avfallskoder.py`
ur förordningstexten i riksdagens öppna data (källa: Sveriges riksdag). Kör
skriptet igen när bilaga 3 ändras; ändringar med senare ikraftträdande får
sina datum och slår igenom av sig själva. `avfallsanteckning/data/kommuner.json`
byggs av `tools/kommuner.py` ur SCB:s lista över kommuner i
kodnummerordning (källa: SCB, CC0).

## Utveckling

Python 3.11 eller senare, Flask, ReportLab, waitress och SQLite. Inga
JavaScript-beroenden, ingen byggkedja.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt ruff
.venv/bin/ruff check .
.venv/bin/python -m unittest discover -s tests
```

CI kör lint, testerna och ett rökprov av containern på varje push. Bilden
publiceras från `main` och från taggar `v*`.

## Licens

MIT, se [LICENSE](LICENSE).
