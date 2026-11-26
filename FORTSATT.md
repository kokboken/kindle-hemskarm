# Fortsätt imorgon – prompt för ny chatt

Öppna en ny chatt **med mappen `C:\Users\victo\Claude_Agents\Kindle` vald** och klistra in texten nedan.

---

Vi fortsätter bygga vår Kindle-hemskärm. Läs först `README.md` (särskilt "Att göra") och `FORTSATT.md` i den här mappen.

**Läget just nu (allt fungerar):**
- Kindle Paperwhite 5 (11:e gen, firmware 5.18.3), jailbreakad med Nosebleed. KUAL fungerar inte – Kindle-delen körs som scriptlets: `kindle/documents/*.sh` (i Kindlens `documents`) och `kindle/homedash/` (i Kindlens rot). Starta: "Hemskärm – starta" i biblioteket. Avsluta: starta om Kindlen.
- Server: Python/Flask (`app.py`, `dash/`) på Render, gratisnivå: https://home-dash-b3n6.onrender.com, deployas automatiskt från GitHub-repot `kokboken/kindle-hemskarm` (privat) via `render.yaml`. Hemligheter ligger bara i Render och i lokala `.env` / `kindle/homedash/nyckel.sh` (båda utanför git) – visa eller skicka dem aldrig.
- Skärmen 1236×1648: stor klocka, Jobbresor (X2 mot Billdal för Victor med "vänta N min" på 25:an mot Balltorp vid Linnéplatsen, räknat på samma X2-turs ankomst; 1:an mot Östra Sjukhuset för Lovisa) / Alla avgångar (bara linje 1, 3, 6, 9, 11, X2, båda håll), väder från Yr, Google Keep-listan "Att köpa" (via eget dashboard-konto).
- Kindlen hämtar båda lägena vid varje minutskifte; tryck på skärmen (pekskärm goodix-ts, /dev/input/event1) byter läge direkt. Mobilsidan `/?key=…` kan också byta läge.

**Att göra, i den här ordningen:**
1. Kopiera nya `kindle/homedash` till Kindlen (ljus 12 dagtid, släckt 23–06, gult ljus 18 från 19:00 via `lipc-set-prop com.lab126.powerd flIntensity` / `currentAmberLevel`). Jag kopplar in Kindlen – den syns som D: – kopiera åt mig och kontrollera sedan `homedash.log` att ljus och värme faktiskt ändras (namnet `currentAmberLevel` är inte bekräftat på PW5).
2. "Snabbast till Brunnsparken" och "Snabbast till Drottningtorget" i jobbvyn via Västtrafiks reseplanerare (Planera Resa v4 journeys), 2 förslag per mål, ingen promenad.
3. Lapp mellan oss: textfält på mobilsidan som visas på Kindlen tills den tas bort.
4. Dagens kalender från vår delade iOS-/iCloud-kalender via dess offentliga iCal-länk (jag lägger in länken i Render själv).
5. Regnvarning för pendlingen ("Ta paraply" om Yr lovar regn när vi går hemifrån).
6. Nattläge 23–06: bara stor klocka och morgondagens väder.

**Lärdomar – följ dessa:**
- Kindle-skript måste ha LF-radbrytningar. Kontrollera med `grep -c $'\r'` och ta bort CR innan något kopieras till Kindlen (Python/git på Windows har gett CRLF).
- Kindlens egen klocka går på UTC – svensk timme kommer från servern (`X-Dash-Hour`).
- Kontrollera att data verkligen är riktig och inte exempeldata (sektioner märks "(EXEMPEL)" när nycklar saknas) innan du säger att något fungerar.
- Ändra aldrig `.env` medan jag kan ha den öppen i Anteckningar. Nycklar läggs in med `scripts/vt_keys.py` och `scripts/keep_token.py`.
- Västtrafik ger bara 2 avgångar per linje om man inte skickar `maxDeparturesPerLineAndDirection`.
- Testa Kindle-skript i simulering på datorn (låtsas-`eips`/`lipc-set-prop`) innan de kopieras.
- Skriv på svenska, och committa + pusha efter varje fungerande steg (Render deployar då automatiskt).

Börja med punkt 1 – säg till när jag ska koppla in Kindlen.
