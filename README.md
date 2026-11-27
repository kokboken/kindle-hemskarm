# Home Dash – Kindle som hemskärm

En gammal Kindle Paperwhite 5 visar spårvagnsavgångar från Järntorget, väder och
handlingslistan från Google Keep.

```
Västtrafik ─┐
Yr (väder) ─┼─▶  molntjänst (Python, Render)  ──▶  dash.png 1236×1648  ──▶  Kindle (hämtar var 3:e min)
Google Keep ┘
```

- **Molntjänsten** (`app.py`, `dash/`) hämtar data och ritar en svartvit bild i
  Kindlens exakta upplösning. Källor som saknar inloggning visar exempeldata,
  och en källa som fallerar visar ett felmeddelande i sin ruta i stället för att
  hela skärmen dör.
- **Kindlen** (jailbreakad) kör `kindle/homedash` via en scriptlet i biblioteket: hämtar
  bilden med `curl` och visar den med `eips`.

## Köra lokalt

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python scripts\fetch_fonts.py
.\.venv\Scripts\python app.py
```

Öppna http://localhost:8000 – du ser bilden som Kindlen kommer att visa.

## Steg för steg

### 1. Jailbreak (klart)
Firmware 5.18.3, jailbreakad med Nosebleed (https://kindlemodding.org/jailbreaking/Nosebleed/).
Sanctuary fungerade inte (rullningslisten till höger). Efteråt: ta bort utfyllnadsfiler och `update*.bin` i roten.

### 2. Västtrafik-nyckel
1. Skapa konto på https://developer.vasttrafik.se
2. Skapa en applikation och prenumerera på **Planera Resa v4**.
3. Kopiera *Client ID* och *Client secret* → `VT_CLIENT_ID`, `VT_CLIENT_SECRET`.

### 3. Google Keep
Google har inget öppet Keep-API för privatkonton, så vi använder det inofficiella
biblioteket `gkeepapi`. Det kräver en så kallad *master token*, som ger full
åtkomst till Google-kontot. Därför:

1. Skapa ett **separat Google-konto** bara för skärmen (t.ex. `vart.hem.dash@gmail.com`).
2. I Keep: dela er handlingslista med det kontot (Lägg till medarbetare).
   Döp listan till **Handla** (eller ändra `KEEP_NOTE_TITLE`).
3. Ta fram en master token för *det nya kontot* enligt gkeepapi-dokumentationen
   (https://gkeepapi.readthedocs.io → "Obtaining a Master Token").
4. Lägg in `KEEP_EMAIL` och `KEEP_MASTER_TOKEN` som miljövariabler i Render –
   aldrig i koden eller i git.

Kan sluta fungera om Google ändrar något; då visar skärmen ett fel i listrutan
men resten fortsätter fungera.

### 4. Lägg upp molntjänsten (Render, gratis)
1. Lägg projektet i ett privat GitHub-repo.
2. Render.com → New → Blueprint → välj repot (`render.yaml` sköter resten).
3. Fyll i miljövariablerna. `DASH_KEY` genereras automatiskt – kopiera den.
4. Testa: `https://<tjänst>.onrender.com/?key=<DASH_KEY>`

Gratisnivån somnar efter 15 min utan trafik; eftersom Kindlen hämtar var 3:e
minut håller den sig vaken. Första hämtningen efter natten kan ta ~1 min.

### 5. Kindlen

KUAL fungerar inte på nya jailbreaks, så skärmen startas med *scriptlets*:
.sh-filer i `documents` som syns som böcker i biblioteket.

1. Ändra `DASH_URL` i `kindle/homedash/settings.sh`.
   Test hemma: `http://<datorns-ip>:8000/dash.png` med `python app.py` igång på datorn.
2. Koppla Kindlen via USB och kopiera:
   - mappen `kindle/homedash` → `homedash` i Kindlens rot
   - filerna i `kindle/documents` → `documents` på Kindlen
3. Mata ut Kindlen. Se till att den är ansluten till ert wifi.
4. Öppna **Hemskärm – starta** i biblioteket.
5. Avsluta: håll in strömknappen och starta om Kindlen.

Ha Kindlen i laddaren – den har wifi på hela tiden. Logg: `homedash.log` i Kindlens rot.

## Jobbresor / Alla avgångar

Skärmen har två lägen:

- **Jobbresor** – bara era linjer (X2 för Victor, 1:an för Lovisa) med fyra avgångar var.
- **Alla avgångar** – allt som går från Järntorget, det som går först överst.

Växla genom att **trycka var som helst på Kindlen** (experimentellt, se nedan) eller
från mobilen: öppna `https://<tjänst>.onrender.com/?key=<DASH_KEY>` och lägg till
sidan på hemskärmen. Där finns två knappar och en förhandsvisning.

Om trycket inte fungerar på Kindlen: kör `cat /proc/bus/input/devices` på Kindlen,
hitta pekskärmens `eventN` och skriv in den som `TOUCH_DEV` i `settings.sh`.

## Testa med riktiga Västtrafik-data på datorn

1. Kopiera `.env.example` till `.env` (ligger utanför git).
2. Fyll i `VT_CLIENT_ID` och `VT_CLIENT_SECRET` i `.env`.
3. Kör `.\.venv\Scripts\python app.py` och öppna http://localhost:8000

## Inställningar

Se `.env.example`. Vanligast:

| Variabel | Vad |
|---|---|
| `VT_WORK` | Jobbresor, t.ex. `X2@Kungälv:Victor,1@Östra:Lovisa` (`@…` = bara den riktningen) |
| `VT_CONNECTIONS` | Byte som visas under en jobbresa, t.ex. `X2=Linnéplatsen:25@Riktning:4` |
| `DEFAULT_MODE` | `jobb` eller `alla` – läget efter omstart av tjänsten |
| `VT_MODES` | "Alla avgångar": t.ex. `tram` för bara spårvagn. Tomt = allt |
| `VT_HIDE_DIRECTIONS` | Dölj riktningar i "Alla avgångar" |
| `KEEP_NOTE_TITLE` | Namnet på listan i Keep |

## Att göra

- [x] Kopiera nya `kindle/homedash` till Kindlen (ljus 12 dag, släckt 23–06, gult från 19, skickar batterinivå) och kontrollera att ljus, värme och batteri fungerar.
- [x] "Snabbast till Brunnsparken / Drottningtorget" i jobbvyn (Västtrafiks reseplanerare, `FASTEST_TO`).
- [x] Lapp: en Keep-anteckning eller -lista som heter "Lapp", delad med dashboard-kontot (listor: obockade rader visas). Kan också skrivas från mobilsidan.
- [x] Kalender (kod klar) – lägg in `ICAL_URL` (iCloud: Kalendrar → ⓘ → Offentlig kalender) i Render → Environment.
- [x] Regnvarning för pendlingen (`COMMUTE_HOURS=7-9`, vardagar).
- [x] Nattläge 23–06 (`NIGHT_START`/`NIGHT_END` på servern, samma timmar som Kindlens ljus).
