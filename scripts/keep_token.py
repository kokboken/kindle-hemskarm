"""Tar fram en Google Keep master token och sparar den i .env.

Kör:  .\\.venv\\Scripts\\python scripts\\keep_token.py

Token skrivs direkt till .env och visas aldrig på skärmen.
Använd BARA dashboard-kontot (inte ditt vanliga Google-konto).
"""
import getpass
import os
import re
import secrets
import sys

import gpsoauth

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")


def read_env():
    if not os.path.exists(ENV):
        sys.exit("Hittar ingen .env – kopiera .env.example till .env först.")
    with open(ENV, encoding="utf-8-sig") as f:
        return f.read()


def main():
    text = read_env()
    m = re.search(r"^KEEP_EMAIL=(.*)$", text, re.M)
    email = (m.group(1).strip() if m else "") or input("Dashboard-kontots e-post: ").strip()

    print(f"""
Konto: {email}

1. Öppna ett privat/inkognito-fönster i webbläsaren.
2. Gå till  https://accounts.google.com/EmbeddedSetup
3. Logga in med {email} och godkänn villkoren.
   (Sidan kan sedan bli tom eller snurra – det är normalt.)
4. Öppna utvecklarverktygen (F12) → fliken Application/Lagring → Cookies
   → accounts.google.com → kopiera värdet för cookien  oauth_token
   (börjar oftast med "oauth2_4/").
""")
    oauth_token = getpass.getpass("Klistra in oauth_token (syns inte när du klistrar) och tryck Enter: ").strip()
    if not oauth_token:
        sys.exit("Inget inklistrat – avbryter.")

    android_id = secrets.token_hex(8)
    res = gpsoauth.exchange_token(email, oauth_token, android_id)
    master = res.get("Token")
    if not master:
        sys.exit(f"Google gav ingen token ({res.get('Error', 'okänt fel')}). "
                 "oauth_token gäller bara några minuter – prova att göra om steg 2–4.")

    print("Fick en token – testar mot Google Keep…")
    import gkeepapi
    keep = gkeepapi.Keep()
    keep.authenticate(email, master)
    titles = sorted({(n.title or "").strip() for n in keep.all() if not n.trashed and n.title})
    print(f"Inloggad! Hittade {len(titles)} anteckningar med titel: {', '.join(titles[:10]) or '–'}")

    if re.search(r"^KEEP_MASTER_TOKEN=.*$", text, re.M):
        text = re.sub(r"^KEEP_MASTER_TOKEN=.*$", lambda _: f"KEEP_MASTER_TOKEN={master}", text, flags=re.M)
    else:
        text += f"\nKEEP_MASTER_TOKEN={master}\n"
    with open(ENV, "w", encoding="utf-8") as f:
        f.write(text)
    print("Sparat i .env. Klart!")


if __name__ == "__main__":
    main()
